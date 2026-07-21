# In-memory server-side store that lets a login survive a browser refresh.

import secrets
from typing import Dict, Optional

_sessions: Dict[str, dict] = {}


def create_session(client, email_address: str) -> str:
    # Store a live client + email under a fresh random token; return the token.
    token = secrets.token_urlsafe(24)
    _sessions[token] = {"client": client, "email_address": email_address}
    return token


def get_session(token: Optional[str]) -> Optional[dict]:
    # Look up a previously created session. Returns None if token is missing/unknown.
    if not token:
        return None
    return _sessions.get(token)


def delete_session(token: Optional[str]) -> None:
    # Drop a stored session, e.g. on logout. Safe to call with None/unknown token.
    if token:
        _sessions.pop(token, None)
