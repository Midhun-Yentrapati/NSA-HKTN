"""Captures things the employee tells Cadence directly.

Until real connectors exist, the employee is the most reliable source of truth
about their own day. "I have a meeting at 5 today", "I've been assigned a course
due 30 September", "I need to review the migration doc, about an hour" - all of
it lands here and becomes part of the same context everything else reasons over.

Anything captured this way is immediately visible to planning, so a meeting
added at 09:00 changes the plan produced at 09:01.
"""

import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence_store import (  # noqa: E402
    events,
    learning,
    next_id,
    now_clock,
    tasks,
    to_minutes,
    today,
    write_event,
    write_learning_item,
    write_task,
)

logger = logging.getLogger(__name__)

VALID_ORIGINS = {
    "organization_mandated", "project_required", "development_plan",
    "manager_assigned", "self_directed",
}


def _clock(value: str, default: str = None) -> str:
    """Normalise a spoken time into HH:MM.

    Handles absolute forms - 5pm, 17:00, 5:30 pm, "at 5" - and relative ones
    like "in 3 hrs" or "in 45 minutes", measured from the pinned demo clock so
    the result is reproducible rather than depending on when it is run.
    """
    if not value:
        return default
    text = str(value).strip().lower().replace(".", "")
    text = re.sub(r"^(at|around|about|by)\s+", "", text)

    # Relative: "in 3 hrs", "in 90 mins", "in an hour", "in half an hour"
    relative = re.match(
        r"^in\s+(an?|half\s+an?|\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", text
    )
    if relative:
        amount_text, unit = relative.group(1), relative.group(2)
        if amount_text.startswith("half"):
            amount = 0.5
        elif amount_text in ("a", "an"):
            amount = 1.0
        else:
            amount = float(amount_text)
        minutes = amount * (60 if unit.startswith(("h", "hr")) else 1)
        total = to_minutes(now_clock()) + int(round(minutes))
        total = max(0, min(total, 23 * 60 + 59))
        return f"{total // 60:02d}:{total % 60:02d}"

    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", text)
    if not match:
        return default
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    elif meridiem is None and hour < 8:
        # "at 5" during a working day means the afternoon, not 5am.
        hour += 12
    return f"{hour:02d}:{minute:02d}"


class Capture(CodedTool):
    """Adds a meeting, task or learning item supplied by the employee."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        kind = (args.get("kind") or "").strip().lower()
        title = (args.get("title") or "").strip()
        if not title:
            return "Error: a title is required. Ask the user what to call it."
        if kind not in ("meeting", "task", "learning"):
            return "Error: kind must be one of 'meeting', 'task' or 'learning'."

        if kind == "meeting":
            return self._meeting(args, title)
        if kind == "task":
            return self._task(args, title)
        return self._learning(args, title)

    # ---------------- meetings ----------------

    def _meeting(self, args: Dict[str, Any], title: str) -> Union[Dict[str, Any], str]:
        date = args.get("date") or today()
        start = _clock(args.get("start"))
        if not start:
            return "Error: a meeting needs a start time. Ask the user what time it starts."

        end = _clock(args.get("end"))
        if not end:
            duration = int(args.get("duration_minutes") or 60)
            end_minutes = to_minutes(start) + duration
            end = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"

        if to_minutes(end) <= to_minutes(start):
            return "Error: the meeting ends at or before it starts."

        existing = events()

        # Idempotency. A failed tool call upstream gets retried, and without this
        # check each retry writes another identical meeting - which is exactly how
        # one "meeting at 5pm" became nine calendar entries that all conflicted
        # with each other.
        for event in existing:
            if (event["date"] == date and event["start"] == start
                    and event["end"] == end and event["title"].strip().lower() == title.lower()):
                return {
                    "status": "already_recorded",
                    "recorded": event,
                    "conflicts": [],
                    "message": (f"'{title}' on {date} from {start} to {end} is already on the "
                                f"calendar as {event['id']}. Nothing new was added."),
                }

        clashes = [
            {"id": e["id"], "title": e["title"], "start": e["start"], "end": e["end"]}
            for e in existing
            if e["date"] == date
            and to_minutes(start) < to_minutes(e["end"])
            and to_minutes(e["start"]) < to_minutes(end)
        ]

        record = {
            "id": next_id("CAL", [e["id"] for e in events()]),
            "date": date, "start": start, "end": end, "title": title,
            "attendees": args.get("attendees") or ["Kiran Rao"],
            "notes": args.get("notes") or "Added by the employee.",
            "source": "user_input",
        }
        outcome = write_event(record)
        return {
            "status": outcome["status"],
            "recorded": record,
            "conflicts": clashes,
            "message": (
                f"Added '{title}' on {date} from {start} to {end} as {record['id']}."
                + (f" It overlaps {len(clashes)} existing meeting(s) - tell the user which."
                   if clashes else "")
                + " Today's free windows have changed; re-plan if a schedule was already given."
            ),
        }

    # ---------------- tasks ----------------

    def _task(self, args: Dict[str, Any], title: str) -> Dict[str, Any]:
        effort = int(args.get("effort_minutes") or 30)
        deadline = args.get("deadline")
        if deadline and len(str(deadline)) == 10:
            deadline = f"{deadline}T17:30"

        record = {
            "id": next_id("USR", [t["id"] for t in tasks()]),
            "title": title,
            "effort_minutes": effort,
            "deep_work": bool(args.get("deep_work", effort >= 60)),
            "interruptibility": args.get("interruptibility") or "medium",
            "deadline": deadline,
            "status": "not_started",
            "assigned_on": today(),
            "blocks": args.get("blocks") or [],
            "depends_on": args.get("depends_on") or [],
            "meeting_dependency": args.get("meeting_dependency"),
            "source": "Added by the employee",
            "project": args.get("project") or "Ad hoc",
            "tags": ["user_input"],
        }
        outcome = write_task(record)
        return {
            "status": outcome["status"],
            "recorded": record,
            "message": (
                f"Added '{title}' as {record['id']}, {effort} minutes"
                + (f", due {deadline}." if deadline else ", no deadline.")
                + (" Marked as deep work since it needs an hour or more."
                   if record["deep_work"] else "")
            ),
        }

    # ---------------- learning ----------------

    def _learning(self, args: Dict[str, Any], title: str) -> Union[Dict[str, Any], str]:
        origin = args.get("origin") or "self_directed"
        if origin not in VALID_ORIGINS:
            return f"Error: origin must be one of {sorted(VALID_ORIGINS)}."

        remaining = int(args.get("remaining_minutes") or 120)
        record = {
            "id": next_id("LRN", [i["id"] for i in learning()]),
            "title": title,
            "origin": origin,
            "why": args.get("why") or "Added by the employee.",
            "deadline": args.get("deadline"),
            "progress_pct": int(args.get("progress_pct") or 0),
            "remaining_minutes": remaining,
            "min_session_minutes": int(args.get("min_session_minutes") or 30),
            "deep_work": bool(args.get("deep_work", True)),
            "relevance_to_current_work": args.get("relevance_to_current_work") or "unknown",
            "consequence_if_missed": args.get("consequence_if_missed") or "Not yet assessed.",
            "source": "user_input",
        }
        outcome = write_learning_item(record)

        urgency = ""
        if record["deadline"]:
            try:
                days = (datetime.fromisoformat(record["deadline"])
                        - datetime.fromisoformat(today())).days
                pace = remaining / max(days, 1)
                urgency = (f" That is {days} days away, so roughly {pace:.0f} minutes a day "
                           f"to finish {remaining} minutes of study.")
            except ValueError:
                urgency = ""

        return {
            "status": outcome["status"],
            "recorded": record,
            "message": (f"Added '{title}' to the learning plan as {record['id']}"
                        + (f", due {record['deadline']}." if record["deadline"] else ".")
                        + urgency),
        }
