"""The single retrieval surface over Kiran's synthetic work context.

Every agent reads the world through this tool. Nothing is invented: agents
reason over records this returns, and cite them by id.
"""

import logging
import os
import sys
from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence_store import (  # noqa: E402
    decisions,
    events,
    learning,
    messages,
    persona,
    tasks,
    today,
    transcript,
)

logger = logging.getLogger(__name__)

ALL_SOURCES = ["tasks", "calendar", "learning", "messages", "decisions", "persona", "transcript"]

# A transcript is thousands of tokens. "all" must not silently drag one in - it is
# returned only when a caller asks for it by name.
DEFAULT_SOURCES = [s for s in ALL_SOURCES if s != "transcript"]

# Every field returned becomes prompt tokens on the next model call, and provider
# quotas are measured in tokens per day. These projections keep exactly the fields
# an agent needs to reason and cite, and drop bookkeeping it never uses.
# Pass full=true to get whole records back.
PROJECTIONS = {
    "tasks": ("id", "title", "effort_minutes", "deep_work", "interruptibility",
              "deadline", "status", "blocks", "depends_on", "meeting_dependency"),
    "calendar": ("id", "date", "start", "end", "title", "presenter", "notes"),
    "messages": ("id", "date", "from", "subject", "importance", "read",
                 "arrived_during_leave", "body"),
    "learning": ("id", "title", "origin", "deadline", "progress_pct",
                 "remaining_minutes", "min_session_minutes",
                 "relevance_to_current_work", "consequence_if_missed"),
    "decisions": ("id", "date", "title", "decision", "rationale",
                  "alternatives_rejected", "note"),
}


def _text_of(record: Dict[str, Any]) -> str:
    """Flatten a record's string content for keyword matching."""
    chunks: List[str] = []
    for value in record.values():
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, list):
            chunks.extend(str(v) for v in value)
        elif isinstance(value, dict):
            chunks.extend(str(v) for v in value.values())
    return " ".join(chunks).lower()


class ContextQuery(CodedTool):
    """Retrieves records across every synthetic source, with optional filters."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        sources = args.get("sources") or "all"
        if isinstance(sources, str):
            sources = DEFAULT_SOURCES if sources.lower() == "all" else [s.strip() for s in sources.split(",")]
        sources = [s for s in sources if s in ALL_SOURCES]

        query = (args.get("query") or "").strip().lower()
        ids = args.get("ids") or []
        if isinstance(ids, str):
            ids = [i.strip() for i in ids.split(",") if i.strip()]
        since = args.get("since")
        until = args.get("until")
        unread_only = bool(args.get("unread_only"))
        # Kept deliberately low. Every record returned becomes prompt tokens on the
        # next model call, and provider quotas are measured in tokens per day.
        limit = int(args.get("limit") or 20)
        full = bool(args.get("full"))

        def keep(record: Dict[str, Any], date_field: str = None) -> bool:
            if ids and record.get("id") not in ids:
                return False
            if query and query not in _text_of(record):
                return False
            if date_field:
                value = (record.get(date_field) or "")[:10]
                if since and value and value < since:
                    return False
                if until and value and value > until:
                    return False
            return True

        result: Dict[str, Any] = {"query_echo": {
            "sources": sources, "query": query or None, "ids": ids or None,
            "since": since, "until": until, "today": today(),
        }}

        if "tasks" in sources:
            result["tasks"] = [t for t in tasks() if keep(t)][:limit]
        if "calendar" in sources:
            result["calendar"] = [e for e in events() if keep(e, "date")][:limit]
        if "learning" in sources:
            result["learning"] = [item for item in learning() if keep(item)][:limit]
        if "messages" in sources:
            found = [m for m in messages() if keep(m, "date")]
            if unread_only:
                found = [m for m in found if not m.get("read")]
            result["messages"] = found[:limit]
        if "decisions" in sources:
            result["decisions"] = [d for d in decisions() if keep(d, "date")][:limit]
        if "persona" in sources:
            result["persona"] = persona()
        if "transcript" in sources:
            text = transcript(args.get("transcript_name") or "auth_kt")
            result["transcript"] = {
                "id": "TR-001",
                "name": args.get("transcript_name") or "auth_kt",
                "available": bool(text),
                "text": text,
            }

        # Trim long free-text fields unless the caller explicitly wants them. A
        # message body or decision rationale in full costs far more tokens than the
        # agent needs to decide what matters.
        # Copy each record first: these come straight from the module-level cache,
        # and trimming in place would permanently truncate the stored data.
        if not full:
            caps = {"messages": 220, "decisions": 400, "calendar": 200}
            for key, fields in PROJECTIONS.items():
                if key not in result:
                    continue
                cap = caps.get(key)
                projected: List[Dict[str, Any]] = []
                for record in result[key]:
                    # Copy field by field: these records come straight from the
                    # module-level cache, and editing in place would permanently
                    # truncate the stored data.
                    copy = {f: record[f] for f in fields if f in record and record[f] not in (None, [], "")}
                    if cap:
                        for field in ("body", "rationale", "notes"):
                            text = copy.get(field)
                            if isinstance(text, str) and len(text) > cap:
                                copy[field] = text[:cap] + " ..."
                    projected.append(copy)
                result[key] = projected

        counts = {k: (len(v) if isinstance(v, list) else 1) for k, v in result.items() if k != "query_echo"}
        result["result_counts"] = counts

        # Always advertise what transcripts exist, whatever was searched. Otherwise an
        # agent that queried the wrong sources concludes the transcript does not exist.
        result["transcripts_available"] = [
            {
                "id": "TR-001",
                "name": "auth_kt",
                "title": "KT session: Helix auth service handover, recorded 2026-09-02 by Devika Suresh",
                "how_to_read": "Call this tool again with sources=transcript and transcript_name=auth_kt",
            }
        ]
        logger.debug("ContextQuery -> %s", counts)
        return result
