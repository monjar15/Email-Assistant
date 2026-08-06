"""Shared metrics for AI summaries and future task-ready items."""
from datetime import date, datetime, timedelta
import re

_EMPTY_ITEM_MARKERS = {
    "",
    "none",
    "none identified",
    "none identified.",
    "n/a",
    "na",
    "no action required",
    "no action required.",
}


def _has_real_values(values) -> bool:
    """Return True when a list-like field contains at least one real value."""
    if not values:
        return False
    if isinstance(values, str):
        values = [values]
    for value in values:
        text = str(value or "").strip().casefold()
        if text and text not in _EMPTY_ITEM_MARKERS:
            return True
    return False


def is_task_ready(summary: dict) -> bool:
    """A summary is task-ready only when it has a real action item."""
    return _has_real_values(summary.get("action_items"))


def todo_task_count(summaries: list[dict]) -> int:
    """Count task records, not individual action-item checklist entries."""
    return sum(1 for item in summaries if is_task_ready(item))


def _priority_key(value) -> str:
    key = str(value or "Medium").strip().casefold()
    return key if key in {"high", "medium", "low"} else "medium"


def _status_key(value) -> str:
    key = str(value or "Pending").strip().casefold().replace("_", " ")
    if key in {"complete", "completed", "done"}:
        return "complete"
    if key in {"in progress", "in-progress", "ongoing"}:
        return "in_progress"
    return "pending"


def summary_overview_counts(summaries: list[dict]) -> dict[str, int]:
    """Return sidebar counts for priorities and actionable-task statuses."""
    counts = {
        "priority_high": 0,
        "priority_medium": 0,
        "priority_low": 0,
        "status_complete": 0,
        "status_in_progress": 0,
        "status_pending": 0,
        "deadline_today": 0,
        "deadline_week": 0,
        "deadline_month": 0,
    }

    for item in summaries:
        counts[f"priority_{_priority_key(item.get('priority'))}"] += 1
        if is_task_ready(item):
            counts[f"status_{_status_key(item.get('status'))}"] += 1
        for window in ("today", "week", "month"):
            if deadline_matches(item, window):
                counts[f"deadline_{window}"] += 1

    return counts


def _deadline_dates(summary: dict) -> list[date]:
    """Extract resolved dates from structured deadline text."""
    values = summary.get("deadlines") or []
    if isinstance(values, str):
        values = [values]
    found = []
    for value in values:
        text = str(value or "")
        for match in re.findall(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text):
            try:
                found.append(date(*(int(part) for part in match)))
            except ValueError:
                pass
    return found


def deadline_matches(summary: dict, window: str, today: date | None = None) -> bool:
    """Return whether any explicit deadline falls within a sidebar window."""
    today = today or datetime.now().date()
    dates = [value for value in _deadline_dates(summary) if value >= today]
    if window == "today" and any(value == today for value in dates):
        return True
    if window == "week" and any(value <= today + timedelta(days=7) for value in dates):
        return True
    if window == "month" and any(
        value.year == today.year and value.month == today.month for value in dates
    ):
        return True

    # Also recognize direct textual output from older summaries that predates
    # the prompt's resolved YYYY-MM-DD suffix.
    values = summary.get("deadlines") or []
    if isinstance(values, str):
        values = [values]
    text = " ".join(str(value or "").casefold() for value in values)
    if window == "today":
        return bool(re.search(r"\b(today|end of day|eod)\b", text))
    if window == "week":
        return bool(re.search(r"\b(today|tomorrow|this week|end of week|eow)\b", text))
    if window == "month":
        return bool(re.search(r"\b(today|tomorrow|this week|this month|end of month|eom)\b", text))
    return False


def deadline_bucket(summary: dict, today: date | None = None) -> str | None:
    """Return the narrowest matching deadline window (compatibility helper)."""
    for window in ("today", "week", "month"):
        if deadline_matches(summary, window, today=today):
            return window
    return None
