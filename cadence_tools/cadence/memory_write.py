"""Writes newly-learned facts back into Kiran's learning plan.

This is what makes the system's memory more than a search box: after ingesting
a knowledge-transfer transcript, asking "what should I learn next?" gives a
different answer than it did before, because state actually changed on disk.
"""

import logging
import os
import sys
from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence_store import learning, write_learning_item  # noqa: E402

logger = logging.getLogger(__name__)

VALID_ORIGINS = {
    "organization_mandated",
    "project_required",
    "development_plan",
    "manager_assigned",
    "self_directed",
}


class MemoryWrite(CodedTool):
    """Adds a learning item derived from ingested material, such as a KT transcript."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        title = (args.get("title") or "").strip()
        if not title:
            return "Error: a title is required to record a learning item."

        existing = learning()
        # Don't create a near-duplicate of something already on the plan.
        lowered = title.lower()
        for item in existing:
            if item["title"].lower() == lowered:
                return {
                    "status": "already_present",
                    "id": item["id"],
                    "message": f"'{title}' is already on the learning plan as {item['id']}.",
                }

        origin = args.get("origin") or "project_required"
        if origin not in VALID_ORIGINS:
            return (f"Error: origin must be one of {sorted(VALID_ORIGINS)}, got '{origin}'.")

        # Allocate the next free LRN id.
        used = {int(i["id"].split("-")[1]) for i in existing if i["id"].startswith("LRN-")}
        new_id = f"LRN-{max(used) + 1:03d}" if used else "LRN-001"

        try:
            remaining = int(args.get("remaining_minutes") or 60)
            min_session = int(args.get("min_session_minutes") or 30)
        except (TypeError, ValueError):
            return "Error: remaining_minutes and min_session_minutes must be whole numbers."

        item = {
            "id": new_id,
            "title": title,
            "origin": origin,
            "why": args.get("why") or "Identified while processing a knowledge-transfer session.",
            "deadline": args.get("deadline"),
            "progress_pct": 0,
            "remaining_minutes": remaining,
            "min_session_minutes": min_session,
            "deep_work": bool(args.get("deep_work", True)),
            "relevance_to_current_work": args.get("relevance_to_current_work") or "high",
            "consequence_if_missed": args.get("consequence_if_missed") or "Not yet assessed.",
            "source": args.get("source") or "Derived from KT transcript TR-001",
        }

        result = write_learning_item(item)
        logger.debug("MemoryWrite -> %s %s", result["status"], new_id)
        return {
            "status": result["status"],
            "id": new_id,
            "item": item,
            "message": f"Recorded '{title}' on the learning plan as {new_id}.",
        }


class MemoryWriteBatch(CodedTool):
    """Records several learning items in one call, for a whole transcript at once."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        items = args.get("items") or []
        if isinstance(items, dict):
            items = items.get("items", [])
        if not items:
            return "Error: no items supplied."

        writer = MemoryWrite()
        written: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        for entry in items:
            outcome = writer.invoke(entry, sly_data)
            if isinstance(outcome, str):
                skipped.append({"title": entry.get("title"), "reason": outcome})
            elif outcome["status"] == "written":
                written.append({"id": outcome["id"], "title": outcome["item"]["title"]})
            else:
                skipped.append({"title": entry.get("title"), "reason": outcome.get("message")})

        return {
            "written_count": len(written),
            "written": written,
            "skipped": skipped,
            "message": (
                f"Added {len(written)} new learning item(s) to the plan"
                + (f"; skipped {len(skipped)} already present." if skipped else ".")
            ),
        }
