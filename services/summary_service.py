"""Business logic for building structured email summaries."""
from services.ai_service import summarize_email


def create_summary(email: dict) -> dict:
    """Build a display-ready summary while preserving email metadata."""
    return {
        "uid": str(email.get("uid", "")),
        "from": email.get("from", ""),
        "to": email.get("to", ""),
        "subject": email.get("subject") or "(No Subject)",
        "date": email.get("date", ""),
        "date_display": email.get("date_display", "Unknown"),
        "snippet": email.get("snippet", ""),
        **summarize_email(email),
    }
