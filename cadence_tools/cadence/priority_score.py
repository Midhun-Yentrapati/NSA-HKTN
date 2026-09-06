"""Explainable, deterministic priority scoring.

The score is decomposed into named components so the agent can say *why* one
item outranks another and cite the arithmetic, rather than asserting an order
the model happens to like.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cadence_store import deadline_parts, events, learning, tasks, today  # noqa: E402

logger = logging.getLogger(__name__)

# Component ceilings. They sum to 100.
W_DEADLINE = 40
W_BLOCKING = 25
W_UNBLOCKS = 15
W_MEETING = 20


class PriorityScore(CodedTool):
    """Scores open work items and explains each component of the score."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        date = args.get("date") or today()
        now = datetime.fromisoformat(f"{date}T09:00")
        all_tasks = tasks()
        day_events = [e for e in events() if e["date"] == date]

        # How many other tasks are waiting on each task.
        unblocks: Dict[str, List[str]] = {}
        for task in all_tasks:
            for prerequisite in task.get("depends_on", []):
                unblocks.setdefault(prerequisite, []).append(task["id"])

        scored: List[Dict[str, Any]] = []

        for task in all_tasks:
            if task.get("status") == "done":
                continue
            components: List[Dict[str, Any]] = []

            # Deadline pressure, measured as slack: time available minus time needed.
            due = deadline_parts(task.get("deadline"))
            if due:
                minutes_left = (due - now).total_seconds() / 60.0
                slack = minutes_left - task["effort_minutes"]
                if slack < 0:
                    points, why = W_DEADLINE, (
                        f"already impossible to finish before the deadline "
                        f"({int(minutes_left)} min left, needs {task['effort_minutes']})")
                elif slack < 120:
                    points, why = W_DEADLINE, (
                        f"only {int(slack)} min of slack after allowing "
                        f"{task['effort_minutes']} min of work")
                elif slack < 60 * 8:
                    points, why = 30, f"{int(slack / 60)}h of slack - due today or tomorrow"
                elif slack < 60 * 24 * 3:
                    points, why = 18, f"{int(slack / 60 / 24)} days of slack"
                else:
                    points, why = 8, f"{int(slack / 60 / 24)} days of slack - not urgent"
            else:
                points, why = 0, "no deadline"
            components.append({"name": "deadline_pressure", "points": points, "max": W_DEADLINE, "why": why})

            # Blocking other people.
            blocks = task.get("blocks", [])
            if blocks:
                components.append({"name": "blocking_others", "points": W_BLOCKING, "max": W_BLOCKING,
                                   "why": "; ".join(blocks)})
            else:
                components.append({"name": "blocking_others", "points": 0, "max": W_BLOCKING,
                                   "why": "blocks nobody"})

            # Unblocking your own downstream work.
            downstream = unblocks.get(task["id"], [])
            if downstream:
                points = min(W_UNBLOCKS, 8 * len(downstream))
                components.append({"name": "unblocks_own_work", "points": points, "max": W_UNBLOCKS,
                                   "why": f"{len(downstream)} task(s) depend on it: {', '.join(downstream)}"})
            else:
                components.append({"name": "unblocks_own_work", "points": 0, "max": W_UNBLOCKS,
                                   "why": "nothing depends on it"})

            # Tied to a meeting happening today.
            meeting_id = task.get("meeting_dependency")
            meeting = next((e for e in day_events if e["id"] == meeting_id), None)
            if meeting:
                components.append({"name": "meeting_dependency", "points": W_MEETING, "max": W_MEETING,
                                   "why": f"needed for '{meeting['title']}' at {meeting['start']} today"})
            else:
                components.append({"name": "meeting_dependency", "points": 0, "max": W_MEETING,
                                   "why": "not tied to a meeting today"})

            total = sum(c["points"] for c in components)
            drivers = [c["why"] for c in components if c["points"] > 0]
            scored.append({
                "id": task["id"],
                "title": task["title"],
                "score": total,
                "effort_minutes": task["effort_minutes"],
                "deep_work": task["deep_work"],
                "deadline": task.get("deadline"),
                "components": components,
                "explanation": f"Scored {total}/100 because " + ("; ".join(drivers) if drivers else "nothing is pressing"),
            })

        scored.sort(key=lambda s: (-s["score"], s["effort_minutes"]))

        # The component breakdown is the interesting part, but only for work that is
        # actually in contention. Returning it for every task in the backlog costs
        # tokens the agent gains nothing from.
        detail_count = int(args.get("detail_count") or 6)
        for entry in scored[detail_count:]:
            entry.pop("components", None)
            entry.pop("explanation", None)

        # Learning items are ranked separately - they compete for time, not for the same queue.
        learning_ranked = []
        for item in learning():
            if item["progress_pct"] >= 100:
                continue
            urgency = "none"
            if item["deadline"]:
                days_left = (datetime.fromisoformat(item["deadline"]) - datetime.fromisoformat(date)).days
                urgency = f"{days_left} days left"
                mandatory = item["origin"] == "organization_mandated"
                pressure = (100 if (mandatory and days_left <= 3) else
                            70 if days_left <= 7 else 40)
            else:
                pressure = 10
            learning_ranked.append({
                "id": item["id"], "title": item["title"], "origin": item["origin"],
                "pressure": pressure, "urgency": urgency,
                "remaining_minutes": item["remaining_minutes"],
                "min_session_minutes": item["min_session_minutes"],
                "why": f"{item['origin'].replace('_', ' ')}; {urgency}; {item['remaining_minutes']} min remaining",
            })
        learning_ranked.sort(key=lambda x: -x["pressure"])

        result = {
            "date": date,
            "scoring_model": {
                "deadline_pressure": W_DEADLINE, "blocking_others": W_BLOCKING,
                "unblocks_own_work": W_UNBLOCKS, "meeting_dependency": W_MEETING,
                "note": "Deterministic. Same inputs always produce the same ranking.",
            },
            "tasks_ranked": scored,
            "learning_ranked": learning_ranked,
        }
        logger.debug("PriorityScore -> top=%s", scored[0]["id"] if scored else None)
        return result
