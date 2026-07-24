import secrets
from typing import Dict, Optional

_sessions: Dict[str, dict] = {}


def create_session(client, email_address: str) -> str:
    # Save the live login under a random session token.
    token = secrets.token_urlsafe(24)
    _sessions[token] = {"client": client, "email_address": email_address}
    return token


def get_session(token: Optional[str]) -> Optional[dict]:
    # Return the saved login for a valid token.
    if not token:
        return None
    return _sessions.get(token)


def delete_session(token: Optional[str]) -> None:
    # Remove the saved login during logout.
    if token:
        _sessions.pop(token, None)
