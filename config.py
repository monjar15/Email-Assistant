"""
Central configuration for the AI Email Assistant (login + fetch phase).
"""

# --------------------------------------------------------------------------
# IMAP settings — supports any IMAP-capable provider.
# KNOWN_PROVIDERS maps common email domains to known-good host/port so
# login can skip autodiscovery. Any domain not listed here falls through
# to live autodiscovery in email_handler/provider_detect.py.
# --------------------------------------------------------------------------
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
    "gmx.com":        {"server": "imap.gmx.com",           "port": 993},
}

# --------------------------------------------------------------------------
# App behavior
# --------------------------------------------------------------------------
MAX_EMAILS_FETCH = 50
