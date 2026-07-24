"""
Central configuration for the AI Email Assistant.
"""

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
    "gmx.com":        {"server": "imap.gmx.com",           "port": 993},
}

# App settings.
MAX_EMAILS_FETCH = 50
