"""Deterministic free-window arithmetic.

LLMs are unreliable at clock arithmetic; Python is not. Every number the
agents reason about for time comes from here, not from a model.
"""

import logging
import os
import sys
from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence_store import events, persona, to_clock, to_minutes, today  # noqa: E402

logger = logging.getLogger(__name__)


class CalendarGaps(CodedTool):
    """Returns the day's meetings and the exact free windows between them."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        date = args.get("date") or today()
        min_minutes = int(args.get("min_minutes") or 0)

        profile = persona()
        day_start = to_minutes(profile["work_hours"]["start"])
        day_end = to_minutes(profile["work_hours"]["end"])

        day_events = sorted(
            [e for e in events() if e["date"] == date],
            key=lambda e: to_minutes(e["start"]),
        )

        windows: List[Dict[str, Any]] = []
        cursor = day_start
        for event in day_events:
            start = to_minutes(event["start"])
            end = to_minutes(event["end"])
            if start > cursor:
                windows.append({"start": to_clock(cursor), "end": to_clock(start), "minutes": start - cursor})
            cursor = max(cursor, end)
        if cursor < day_end:
            windows.append({"start": to_clock(cursor), "end": to_clock(day_end), "minutes": day_end - cursor})

        windows = [w for w in windows if w["minutes"] >= min_minutes]
        longest = max((w["minutes"] for w in windows), default=0)

        result = {
            "date": date,
            "work_hours": profile["work_hours"],
            "meetings": [
                {
                    "id": e["id"],
                    "start": e["start"],
                    "end": e["end"],
                    "title": e["title"],
                    "presenter": e.get("presenter"),
                }
                for e in day_events
            ],
            "free_windows": windows,
            "total_free_minutes": sum(w["minutes"] for w in windows),
            "longest_free_window_minutes": longest,
            "deep_work_min_block_minutes": profile["working_preferences"]["deep_work_min_block_minutes"],
            "note": (
                f"No single free window on {date} exceeds {longest} minutes. "
                "Any task needing more uninterrupted time than that cannot be finished today."
            ),
        }
        logger.debug("CalendarGaps -> %s windows, longest %s min", len(windows), longest)
        return result
