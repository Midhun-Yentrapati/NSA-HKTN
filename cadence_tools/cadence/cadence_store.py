"""Shared synthetic-data access for the Cadence agent network.

All data is fabricated. No real people, companies or personal data are used.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

_CACHE: Dict[str, Any] = {}


def _load(name: str) -> Dict[str, Any]:
    if name not in _CACHE:
        with open(os.path.join(DATA_DIR, f"{name}.json"), "r", encoding="utf-8") as handle:
            _CACHE[name] = json.load(handle)
    return _CACHE[name]


def persona() -> Dict[str, Any]:
    return _load("persona")


def today() -> str:
    """The pinned demo date, so runs are reproducible regardless of wall clock."""
    return persona()["demo_today"]


def now_clock() -> str:
    """The pinned wall-clock time inside the demo, so "in 3 hours" is reproducible."""
    return persona().get("demo_now", "09:30")


def tasks() -> List[Dict[str, Any]]:
    return _load("tasks")["tasks"]


def events() -> List[Dict[str, Any]]:
    return _load("calendar")["events"]


def learning() -> List[Dict[str, Any]]:
    return _load("learning")["items"]


def messages() -> List[Dict[str, Any]]:
    return _load("messages")["messages"]


def decisions() -> List[Dict[str, Any]]:
    return _load("decisions")["records"]


def transcript(name: str = "auth_kt") -> str:
    path = os.path.join(DATA_DIR, "transcripts", f"{name}.txt")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write_learning_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Append a learning item to disk so ingestion visibly changes system state."""
    data = _load("learning")
    if any(existing["id"] == item["id"] for existing in data["items"]):
        return {"status": "already_present", "id": item["id"]}
    data["items"].append(item)
    with open(os.path.join(DATA_DIR, "learning.json"), "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return {"status": "written", "id": item["id"]}


def _persist(name: str, key: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Append a record to one of the JSON stores and write it back to disk."""
    data = _load(name)
    if any(existing.get("id") == record["id"] for existing in data[key]):
        return {"status": "already_present", "id": record["id"]}
    data[key].append(record)
    with open(os.path.join(DATA_DIR, f"{name}.json"), "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return {"status": "written", "id": record["id"]}


def next_id(prefix: str, existing_ids: List[str]) -> str:
    """Allocate the next free id for a prefix, e.g. CAL-134."""
    numbers = []
    for value in existing_ids:
        if value.startswith(f"{prefix}-"):
            tail = value.split("-", 1)[1]
            if tail.isdigit():
                numbers.append(int(tail))
    return f"{prefix}-{(max(numbers) + 1) if numbers else 1:03d}"


def write_event(record: Dict[str, Any]) -> Dict[str, Any]:
    return _persist("calendar", "events", record)


def write_task(record: Dict[str, Any]) -> Dict[str, Any]:
    return _persist("tasks", "tasks", record)


def to_minutes(clock: str) -> int:
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def to_clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def deadline_parts(deadline: Optional[str]) -> Optional[datetime]:
    if not deadline:
        return None
    text = deadline if "T" in deadline else f"{deadline}T17:30"
    return datetime.fromisoformat(text)
