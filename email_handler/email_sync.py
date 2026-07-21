import imaplib
from typing import Dict

from . import email_parser
from storage.email_store import EmailStore
from .imap_client import IMAPClient


def sync_folder(imap_client: IMAPClient, store: EmailStore,
                 folder: str = "INBOX", limit: int = 50, offset: int = 0,
                 refresh: bool = False) -> Dict:
    # Fetch one page of headers from `folder` and save them to the
    # local store. Falls back gracefully if there's no connection.
    #
    # Returns:
    #     {"ok": True, "total": int, "has_more": bool, "count": int}
    #     or
    #     {"ok": False, "error": str}  -- caller should use store.get_page()
    #     to show the last-synced data instead.
    try:
        raw = imap_client.fetch_inbox(folder, limit=limit, offset=offset, refresh=refresh)
    except (ConnectionError, imaplib.IMAP4.error, OSError) as e:
        return {"ok": False, "error": f"Could not reach mail server: {e}"}

    parsed = [
        email_parser.parse_email(e["raw"], e["uid"])
        for e in raw["emails"]
    ]

    try:
        store.save_page(folder, parsed)
    except Exception as e:
        print(f"[email_sync] FAILED to store emails to database "
              f"(folder='{folder}'): {e}")
        return {"ok": False, "error": f"Fetched OK but failed to save to database: {e}"}

    return {
        "ok": True,
        "total": raw["total"],
        "has_more": raw["has_more"],
        "count": len(parsed),
    }


def sync_message(imap_client: IMAPClient, store: EmailStore,
                  folder: str, uid: str) -> Dict:
    # Fetch the full body of one message and save it to the local
    # store. Falls back gracefully if there's no connection.
    #
    # Returns:
    #     {"ok": True, "email": {...}}  -- full parsed record, also saved
    #     or
    #     {"ok": False, "error": str, "cached": {...} or None}  -- caller
    #     should show `cached` (whatever's already stored locally, which
    #     may only have header-depth fields) instead of a blank screen.
    try:
        raw = imap_client.fetch_single(folder, uid)
    except (ConnectionError, imaplib.IMAP4.error, OSError) as e:
        return {
            "ok": False,
            "error": f"Could not reach mail server: {e}",
            "cached": store.get_email(folder, uid),
        }

    if raw is None:
        return {
            "ok": False,
            "error": "Message not found on server",
            "cached": store.get_email(folder, uid),
        }

    parsed = email_parser.parse_email(raw, uid)

    try:
        store.save_full(folder, parsed)
    except Exception as e:
        print(f"[email_sync] FAILED to store full message to database "
              f"(folder='{folder}', uid={uid}): {e}")
        return {
            "ok": False,
            "error": f"Fetched OK but failed to save to database: {e}",
            "cached": store.get_email(folder, uid),
        }

    return {"ok": True, "email": parsed}


def get_inbox(imap_client: IMAPClient, store: EmailStore,
              folder: str = "INBOX", limit: int = 50, offset: int = 0) -> Dict:
    # Convenience for the list view: try to sync from the server first;
    # if that fails (offline), transparently serve the local cache instead.
    # Either way, the caller gets the same {"emails", "total", "has_more"}
    # shape and doesn't need to branch on connectivity itself.
    result = sync_folder(imap_client, store, folder, limit, offset)
    if result["ok"]:
        return store.get_page(folder, limit, offset)
    # Offline (or server error) -- fall back to whatever was last synced.
    page = store.get_page(folder, limit, offset)
    page["offline"] = True
    page["error"] = result["error"]
    return page


def get_message(imap_client: IMAPClient, store: EmailStore,
                folder: str, uid: str) -> Dict:
    # Convenience for opening a single message: try to fetch the full
    # body; if that fails, fall back to whatever's cached (which may be
    # header-only if this message was never opened while online before).
    result = sync_message(imap_client, store, folder, uid)
    if result["ok"]:
        return {"email": result["email"], "offline": False}

    cached = result["cached"]
    return {
        "email": cached,
        "offline": True,
        "error": result["error"],
        # Lets the UI show "full message unavailable offline" instead
        # of silently rendering an empty body.
        "body_available": bool(cached and cached.get("is_full")),
    }
