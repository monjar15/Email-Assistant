"""Ollama adapter for structured email summarization with Qwen3."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import OLLAMA_MODEL, OLLAMA_TAGS_URL, OLLAMA_URL


def get_ollama_status() -> dict:
    """Check the local Ollama service without downloading or installing anything."""
    try:
        with urlopen(OLLAMA_TAGS_URL, timeout=1.5) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
        return {"available": False, "model_ready": False}

    names = {str(model.get("name", "")) for model in models}
    return {
        "available": True,
        "model_ready": OLLAMA_MODEL in names,
    }


def _email_text(email: dict) -> str:
    """Build a bounded plain-text prompt payload from one email."""
    body = (email.get("body_text") or email.get("snippet") or "").strip()
    return (
        f"From: {email.get('from', '')}\n"
        f"To: {email.get('to', '')}\n"
        f"Subject: {email.get('subject', '')}\n"
        f"Date: {email.get('date_display', email.get('date', ''))}\n\n"
        f"Email body:\n{body[:12000]}"
    )


def _normalize_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_priority(value) -> str:
    priority = str(value or "medium").strip().casefold()
    return priority.title() if priority in {"high", "medium", "low"} else "Medium"


def _normalize_status(value) -> str:
    status = str(value or "pending").strip().casefold().replace("_", " ")
    aliases = {
        "complete": "Complete",
        "completed": "Complete",
        "done": "Complete",
        "in progress": "In Progress",
        "in-progress": "In Progress",
        "ongoing": "In Progress",
        "pending": "Pending",
        "not started": "Pending",
        "to do": "Pending",
        "todo": "Pending",
    }
    return aliases.get(status, "Pending")


def summarize_email(email: dict) -> dict:
    """Ask the local Qwen3 model for a strictly structured email summary."""
    prompt = """Summarize the email below for a busy professional. Return JSON only,
using exactly these keys: summary (string), priority (High, Medium, or Low),
status (Complete, In Progress, or Pending), key_points (array of strings),
deadlines (array of strings), action_items (array of strings).

Rules:
- Do not invent facts, dates, actions, or progress.
- Determine priority using these rules:
  * High: an explicit urgent/critical/escalated request, a deadline within 24 hours,
    a blocking issue, or a serious consequence if action is delayed.
  * Medium: a clear request that needs attention, a deadline later than 24 hours
    but within 7 days, or routine work with a stated due date.
  * Low: informational or optional mail, no action is requested, or an action has
    no stated urgency or near-term consequence.
  If signals conflict, select the highest applicable priority. Do not treat words
  in signatures, disclaimers, or quoted history as priority signals.
- Use Complete only when the email explicitly says the work is finished or completed.
- Use In Progress only when the email explicitly says the work has started or is ongoing.
- Use Pending for a new request, work not yet started, or when progress is unclear.
- Detect deadlines written as natural-language text as well as numeric dates. This
  includes phrases such as "today", "tomorrow", "this Friday", "next week",
  "end of day", "end of month", and "within three days". Preserve each deadline's
  original wording; when it can be resolved from the email Date, append the resolved
  date in YYYY-MM-DD form, for example "this Friday (2026-08-07)".
- Only include text that actually expresses when something is due; do not mistake
  the sent date, meeting history, or dates in signatures/quoted history for deadlines.
- Use an empty array when there are no deadlines or action items.
- Keep the summary concise and useful.

""" + _email_text(email)
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0.2},
    }
    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama could not run {OLLAMA_MODEL}: {detail}") from error
    except URLError as error:
        raise RuntimeError(
            "Could not connect to Ollama. Start Ollama, then run "
            f"'ollama pull {OLLAMA_MODEL}'."
        ) from error
    except (json.JSONDecodeError, TimeoutError) as error:
        raise RuntimeError("Ollama returned an invalid or incomplete response.") from error

    try:
        content = result["message"]["content"]
        summary = json.loads(content)
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("Qwen3 did not return the expected summary format.") from error

    overview = str(summary.get("summary", "")).strip()
    return {
        "summary": overview or "No summary was generated.",
        "priority": _normalize_priority(summary.get("priority")),
        "status": _normalize_status(summary.get("status")),
        "key_points": _normalize_list(summary.get("key_points")),
        "deadlines": _normalize_list(summary.get("deadlines")),
        "action_items": _normalize_list(summary.get("action_items")),
    }
