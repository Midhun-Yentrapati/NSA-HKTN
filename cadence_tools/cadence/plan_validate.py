"""Hard-constraint checker for a proposed day plan.

This is the engine behind the PlanCritic agent. It uses no LLM and holds no
opinions - it reports objective, reproducible violations. The critic agent
turns these into feedback and the planner revises. That loop is the point.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence_store import (  # noqa: E402
    deadline_parts,
    events,
    learning,
    persona,
    tasks,
    to_minutes,
    today,
)

logger = logging.getLogger(__name__)

BLOCKER = "blocker"
WARNING = "warning"


class PlanValidate(CodedTool):
    """Validates a proposed schedule against calendar, effort, deadline and dependency constraints."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        blocks = args.get("plan") or []
        if isinstance(blocks, dict):
            blocks = blocks.get("plan", [])
        if not blocks:
            return {
                "valid": False,
                "violations": [
                    {
                        "severity": BLOCKER,
                        "code": "EMPTY_PLAN",
                        "item_id": None,
                        "message": "No plan was supplied to validate.",
                    }
                ],
            }

        date = args.get("date") or today()
        profile = persona()
        prefs = profile["working_preferences"]
        task_by_id = {t["id"]: t for t in tasks()}
        learn_by_id = {item["id"]: item for item in learning()}
        day_events = [e for e in events() if e["date"] == date]
        midnight = datetime.fromisoformat(f"{date}T00:00")

        violations: List[Dict[str, Any]] = []

        def flag(severity: str, code: str, item_id: Any, message: str) -> None:
            violations.append({"severity": severity, "code": code, "item_id": item_id, "message": message})

        parsed: List[Dict[str, Any]] = []
        for block in blocks:
            item_id = block.get("item_id") or block.get("id")
            try:
                start = to_minutes(block["start"])
                end = to_minutes(block["end"])
            except (KeyError, ValueError):
                flag(BLOCKER, "MALFORMED_BLOCK", item_id, f"Block for {item_id} has an unreadable start or end time.")
                continue
            if end <= start:
                flag(BLOCKER, "NEGATIVE_DURATION", item_id, f"Block for {item_id} ends at or before it starts.")
                continue
            parsed.append({"item_id": item_id, "start": start, "end": end, "minutes": end - start, "raw": block})
        parsed.sort(key=lambda b: b["start"])

        day_start = to_minutes(profile["work_hours"]["start"])
        day_end = to_minutes(profile["work_hours"]["end"])
        deep_minutes = 0
        scheduled_ids = [b["item_id"] for b in parsed]
        first_start: Dict[str, int] = {}
        for block in parsed:
            first_start.setdefault(block["item_id"], block["start"])

        for index, block in enumerate(parsed):
            item_id = block["item_id"]
            task = task_by_id.get(item_id)
            item = learn_by_id.get(item_id)
            label = block["raw"].get("title") or item_id

            if not task and not item:
                flag(BLOCKER, "UNKNOWN_ITEM", item_id, f"'{item_id}' is not a known task or learning item.")
                continue

            # 1. Inside working hours.
            if block["start"] < day_start or block["end"] > day_end:
                flag(
                    BLOCKER,
                    "OUTSIDE_WORK_HOURS",
                    item_id,
                    f"{label} is scheduled outside working hours "
                    f"({profile['work_hours']['start']}-{profile['work_hours']['end']}).",
                )

            # 2. Does not collide with a meeting.
            for event in day_events:
                estart, eend = to_minutes(event["start"]), to_minutes(event["end"])
                if block["start"] < eend and estart < block["end"]:
                    flag(
                        BLOCKER,
                        "MEETING_COLLISION",
                        item_id,
                        f"{label} overlaps '{event['title']}' ({event['start']}-{event['end']}).",
                    )

            # 3. Does not collide with another planned block.
            if index + 1 < len(parsed) and parsed[index + 1]["start"] < block["end"]:
                flag(
                    BLOCKER,
                    "DOUBLE_BOOKED",
                    item_id,
                    f"{label} overlaps the next planned block ({parsed[index + 1]['item_id']}).",
                )

            if task:
                allocated = sum(b["minutes"] for b in parsed if b["item_id"] == item_id)

                # 4. Uninterruptible work cannot be part-allocated or split across gaps.
                if task["deep_work"] and allocated < task["effort_minutes"]:
                    flag(
                        BLOCKER,
                        "INSUFFICIENT_TIME",
                        item_id,
                        f"{label} needs {task['effort_minutes']} uninterrupted minutes but only "
                        f"{allocated} are allocated. It is marked deep_work, so it cannot be split "
                        f"across gaps and cannot be completed today.",
                    )

                # 5. Deep work needs a minimum viable block.
                if task["deep_work"]:
                    deep_minutes += block["minutes"]
                    # A block is fragmented only if it is shorter than both the work itself
                    # and the stated minimum. A 60-minute task in a 60-minute block is fine.
                    viable = min(task["effort_minutes"], prefs["deep_work_min_block_minutes"])
                    if block["minutes"] < viable:
                        flag(
                            WARNING,
                            "SHORT_DEEP_BLOCK",
                            item_id,
                            f"{label} is deep work in a {block['minutes']}-minute block; "
                            f"{viable} minutes is the smallest useful block for it.",
                        )

                # 6. Deadline respected.
                due = deadline_parts(task.get("deadline"))
                if due and midnight + timedelta(minutes=block["end"]) > due:
                    flag(
                        BLOCKER,
                        "DEADLINE_MISSED",
                        item_id,
                        f"{label} is scheduled to finish at {block['raw']['end']} on {date}, "
                        f"after its deadline of {task['deadline']}.",
                    )

                # 7. Preparation must finish before the meeting it prepares for.
                dep_meeting = task.get("meeting_dependency")
                if dep_meeting:
                    meeting = next((e for e in day_events if e["id"] == dep_meeting), None)
                    if meeting and block["end"] > to_minutes(meeting["start"]):
                        flag(
                            BLOCKER,
                            "PREP_AFTER_MEETING",
                            item_id,
                            f"{label} prepares for '{meeting['title']}', which starts at "
                            f"{meeting['start']}, but it is scheduled to run until {block['raw']['end']}. "
                            f"Preparation must finish before the meeting begins.",
                        )

                # 8. Prerequisites scheduled first.
                for prerequisite in task.get("depends_on", []):
                    if prerequisite in task_by_id and prerequisite in scheduled_ids:
                        if first_start[item_id] < first_start.get(prerequisite, 10**6):
                            flag(
                                BLOCKER,
                                "DEPENDENCY_ORDER",
                                item_id,
                                f"{label} depends on {prerequisite}, which is scheduled later in the same plan.",
                            )

            if item and block["minutes"] < item.get("min_session_minutes", 0):
                flag(
                    WARNING,
                    "SHORT_LEARNING_BLOCK",
                    item_id,
                    f"{label} is allocated {block['minutes']} minutes; "
                    f"{item['min_session_minutes']} is the minimum useful session.",
                )

        # 9. Mandatory learning near its deadline must appear somewhere in the plan.
        for item in learning():
            if item["origin"] != "organization_mandated" or not item["deadline"]:
                continue
            days_left = (datetime.fromisoformat(item["deadline"]) - datetime.fromisoformat(date)).days
            if days_left <= 3 and item["id"] not in scheduled_ids:
                flag(
                    BLOCKER,
                    "MANDATORY_LEARNING_OMITTED",
                    item["id"],
                    f"'{item['title']}' is mandatory, {item['remaining_minutes']} minutes remain and it is "
                    f"due in {days_left} days, but it does not appear in the plan.",
                )

        # 10. Sustainable amount of deep work.
        if deep_minutes > prefs["max_deep_work_minutes_per_day"]:
            flag(
                WARNING,
                "DEEP_WORK_OVERLOAD",
                None,
                f"The plan contains {deep_minutes} minutes of deep work against a stated daily maximum "
                f"of {prefs['max_deep_work_minutes_per_day']}.",
            )

        blockers = [v for v in violations if v["severity"] == BLOCKER]
        result = {
            "valid": not blockers,
            "date": date,
            "blocker_count": len(blockers),
            "warning_count": len(violations) - len(blockers),
            "violations": violations,
            "verdict": (
                "Plan is schedulable."
                if not blockers
                else f"Plan rejected: {len(blockers)} hard constraint violation(s). Revise and resubmit."
            ),
        }
        logger.debug("PlanValidate -> valid=%s blockers=%s", result["valid"], len(blockers))
        return result
