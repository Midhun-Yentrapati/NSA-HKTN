"""Builds a valid day plan deterministically.

Asking a language model to construct a schedule and then rejecting it until it
gets the arithmetic right is slow and does not converge. Constructing the plan
in Python is instant and correct by design; the model's job is to explain the
result and handle the conversation, which is what it is good at.

PlanCritic still validates the output independently - that check is what proves
the plan is sound rather than merely asserted.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from neuro_san.interfaces.coded_tool import CodedTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence_store import (  # noqa: E402
    deadline_parts,
    events,
    learning,
    persona,
    tasks,
    to_clock,
    to_minutes,
    today,
)

logger = logging.getLogger(__name__)


class PlanBuilder(CodedTool):
    """Produces a constraint-satisfying schedule, plus what did not fit and why."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        date = args.get("date") or today()
        must_include = args.get("must_include") or []
        if isinstance(must_include, str):
            must_include = [t.strip() for t in must_include.split(",") if t.strip()]

        profile = persona()
        prefs = profile["working_preferences"]
        max_deep = prefs["max_deep_work_minutes_per_day"]

        windows = self._free_windows(date, profile)
        all_tasks = {t["id"]: t for t in tasks()}
        day_events = [e for e in events() if e["date"] == date]
        midnight = datetime.fromisoformat(f"{date}T00:00")

        plan: List[Dict[str, Any]] = []
        unscheduled: List[Dict[str, str]] = []
        scheduled_ids: List[str] = []
        deep_used = 0

        candidates = self._ranked_candidates(date, all_tasks, must_include)

        for item in candidates:
            latest_end = self._latest_end(item, day_events, midnight, date)

            if item["deep_work"] and item["effort_minutes"] > max((w["minutes"] for w in windows), default=0):
                unscheduled.append({
                    "id": item["id"], "title": item["title"],
                    "reason": (f"needs {item['effort_minutes']} uninterrupted minutes; the longest free "
                               f"window today is {max((w['minutes'] for w in windows), default=0)}"),
                })
                continue

            if item["deep_work"] and deep_used + item["effort_minutes"] > max_deep:
                unscheduled.append({
                    "id": item["id"], "title": item["title"],
                    "reason": f"would push deep work past the {max_deep} minute daily limit",
                })
                continue

            earliest_start = self._earliest_start(item, plan, all_tasks)
            slot = self._first_fit(windows, item["effort_minutes"], earliest_start, latest_end)

            if slot is None:
                unscheduled.append({
                    "id": item["id"], "title": item["title"],
                    "reason": self._why_no_slot(item, latest_end, windows),
                })
                continue

            plan.append({
                "start": to_clock(slot[0]),
                "end": to_clock(slot[0] + item["effort_minutes"]),
                "item_id": item["id"],
                "title": item["title"],
                "kind": item["kind"],
                "reason": item["reason"],
            })
            scheduled_ids.append(item["id"])
            if item["deep_work"]:
                deep_used += item["effort_minutes"]
            self._consume(windows, slot[0], slot[0] + item["effort_minutes"])

        plan.sort(key=lambda b: to_minutes(b["start"]))

        blocked_requests = [
            {"id": rid, "reason": next((u["reason"] for u in unscheduled if u["id"] == rid), "not scheduled")}
            for rid in must_include if rid not in scheduled_ids
        ]

        result = {
            "date": date,
            "plan": plan,
            "scheduled_count": len(plan),
            "unscheduled": unscheduled,
            "deep_work_minutes_used": deep_used,
            "remaining_free_minutes": sum(w["minutes"] for w in windows),
            "requested_but_impossible": blocked_requests,
            "note": (
                "This plan was constructed to satisfy every hard constraint. "
                "Send it to PlanCritic to confirm before presenting it."
            ),
        }
        logger.debug("PlanBuilder -> %s blocks, %s unscheduled", len(plan), len(unscheduled))
        return result

    # ---------------- internals ----------------

    @staticmethod
    def _free_windows(date: str, profile: Dict[str, Any]) -> List[Dict[str, int]]:
        day_start = to_minutes(profile["work_hours"]["start"])
        day_end = to_minutes(profile["work_hours"]["end"])
        booked = sorted(
            ((to_minutes(e["start"]), to_minutes(e["end"])) for e in events() if e["date"] == date),
        )
        windows: List[Dict[str, int]] = []
        cursor = day_start
        for start, end in booked:
            if start > cursor:
                windows.append({"start": cursor, "end": start, "minutes": start - cursor})
            cursor = max(cursor, end)
        if cursor < day_end:
            windows.append({"start": cursor, "end": day_end, "minutes": day_end - cursor})
        return windows

    def _ranked_candidates(self, date: str, all_tasks: Dict[str, Any],
                           must_include: List[str]) -> List[Dict[str, Any]]:
        """Order work by obligation strength: forced first, then mandatory learning, then score."""
        from priority_score import PriorityScore  # local import keeps module load cheap

        scores = PriorityScore().invoke({"date": date}, {})
        ranked = {s["id"]: s for s in scores["tasks_ranked"]}

        candidates: List[Dict[str, Any]] = []

        # 1. Anything the user explicitly asked for comes first.
        for tid in must_include:
            task = all_tasks.get(tid)
            if task:
                candidates.append(self._as_candidate(task, "you asked for this to be scheduled today"))

        # 2. Mandatory learning close to its deadline is non-negotiable.
        for item in learning():
            if item["origin"] != "organization_mandated" or not item["deadline"]:
                continue
            days_left = (datetime.fromisoformat(item["deadline"]) - datetime.fromisoformat(date)).days
            if days_left <= 3:
                candidates.append({
                    "id": item["id"], "title": item["title"], "kind": "learning",
                    "effort_minutes": min(item["remaining_minutes"], 60),
                    "deep_work": False, "deadline": None, "meeting_dependency": None,
                    "depends_on": [],
                    "reason": f"mandatory, due in {days_left} days",
                })

        # 3. Everything else by score.
        for task in sorted(all_tasks.values(),
                           key=lambda t: -ranked.get(t["id"], {}).get("score", 0)):
            if task["id"] in must_include or task.get("status") == "done":
                continue
            score = ranked.get(task["id"], {}).get("score", 0)
            candidates.append(self._as_candidate(task, f"priority score {score}/100"))

        return candidates

    @staticmethod
    def _as_candidate(task: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "id": task["id"], "title": task["title"], "kind": "task",
            "effort_minutes": task["effort_minutes"], "deep_work": task["deep_work"],
            "deadline": task.get("deadline"), "meeting_dependency": task.get("meeting_dependency"),
            "depends_on": task.get("depends_on", []), "reason": reason,
        }

    @staticmethod
    def _latest_end(item: Dict[str, Any], day_events: List[Dict[str, Any]],
                    midnight: datetime, date: str) -> Optional[int]:
        """The latest minute-of-day this item may finish, or None for no constraint."""
        limits: List[int] = []
        meeting_id = item.get("meeting_dependency")
        if meeting_id:
            meeting = next((e for e in day_events if e["id"] == meeting_id), None)
            if meeting:
                limits.append(to_minutes(meeting["start"]))
        due = deadline_parts(item.get("deadline"))
        if due and due.date().isoformat() == date:
            limits.append(int((due - midnight).total_seconds() // 60))
        return min(limits) if limits else None

    @staticmethod
    def _earliest_start(item: Dict[str, Any], plan: List[Dict[str, Any]],
                        all_tasks: Dict[str, Any]) -> int:
        """Never start before a prerequisite that is already in the plan has finished."""
        earliest = 0
        for prerequisite in item.get("depends_on", []):
            block = next((b for b in plan if b["item_id"] == prerequisite), None)
            if block:
                earliest = max(earliest, to_minutes(block["end"]))
        return earliest

    @staticmethod
    def _first_fit(windows: List[Dict[str, int]], minutes: int,
                   earliest_start: int, latest_end: Optional[int]):
        for window in windows:
            start = max(window["start"], earliest_start)
            if start + minutes > window["end"]:
                continue
            if latest_end is not None and start + minutes > latest_end:
                continue
            return (start, start + minutes)
        return None

    @staticmethod
    def _consume(windows: List[Dict[str, int]], start: int, end: int) -> None:
        for window in windows:
            if window["start"] <= start and end <= window["end"]:
                # Keep the remainder after the booked block; the sliver before it is
                # left unused rather than fragmenting the day into unusable scraps.
                window["start"] = end
                window["minutes"] = window["end"] - window["start"]
                break
        windows[:] = [w for w in windows if w["minutes"] > 0]

    @staticmethod
    def _why_no_slot(item: Dict[str, Any], latest_end: Optional[int],
                     windows: List[Dict[str, int]]) -> str:
        if latest_end is not None:
            usable = [w for w in windows if w["start"] + item["effort_minutes"] <= min(w["end"], latest_end)]
            if not usable:
                return (f"must finish by {to_clock(latest_end)} and no free window before then is "
                        f"long enough for {item['effort_minutes']} minutes")
        remaining = max((w["minutes"] for w in windows), default=0)
        return (f"needs {item['effort_minutes']} minutes; only {remaining} contiguous minutes "
                f"remain unbooked today")
