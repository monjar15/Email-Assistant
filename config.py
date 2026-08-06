"""
Central configuration for the AI Email Assistant.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load .env from the same folder as this config.py file.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# Known IMAP providers used before live autodetection.
KNOWN_PROVIDERS = {
    "gmail.com":      {"server": "imap.gmail.com",        "port": 993},
    "googlemail.com": {"server": "imap.gmail.com",        "port": 993},
    "outlook.com":    {"server": "outlook.office365.com", "port": 993},
    "hotmail.com":    {"server": "outlook.office365.com", "port": 993},
    "live.com":       {"server": "outlook.office365.com", "port": 993},
    "yahoo.com":      {"server": "imap.mail.yahoo.com",   "port": 993},
    "yahoo.co.uk":    {"server": "imap.mail.yahoo.com",   "port": 993},
    "icloud.com":     {"server": "imap.mail.me.com",      "port": 993},
    "me.com":         {"server": "imap.mail.me.com",      "port": 993},
    "aol.com":        {"server": "imap.aol.com",          "port": 993},
    "zoho.com":       {"server": "imap.zoho.com",         "port": 993},
    "gmx.com":        {"server": "imap.gmx.com",          "port": 993},
}


# App settings.
MAX_EMAILS_FETCH = 50


# Local LLM settings. Install Ollama and pull the model with:
# ollama pull qwen3:1.7b
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
OLLAMA_MODEL = "qwen3:1.7b"


# Microsoft Entra ID / Microsoft Graph OAuth settings.
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()
MICROSOFT_AUTHORITY = os.getenv(
    "MICROSOFT_AUTHORITY",
    "https://login.microsoftonline.com/common",
).strip()
MICROSOFT_REDIRECT_URI = os.getenv(
    "MICROSOFT_REDIRECT_URI",
    "http://localhost:8501",
).strip()

# Delegated Microsoft Graph permissions requested during sign-in.
# MSAL automatically adds the OpenID Connect and offline-access scopes it needs.
MICROSOFT_SCOPES = os.getenv(
    "MICROSOFT_SCOPES",
    "User.Read Mail.Read",
).split()

# Useful for disabling the Microsoft login button until the two required
# credentials have been entered in .env.
MICROSOFT_OAUTH_CONFIGURED = bool(
    MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET
)


def get_missing_microsoft_settings() -> list[str]:
    """Return the names of required Microsoft OAuth settings that are missing."""
    missing = []

    if not MICROSOFT_CLIENT_ID:
        missing.append("MICROSOFT_CLIENT_ID")

    if not MICROSOFT_CLIENT_SECRET:
        missing.append("MICROSOFT_CLIENT_SECRET")

    return missing
