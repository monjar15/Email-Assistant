# Email service: fetch, parse, cache, search, and one-time full sync.
from email_handler.email_parser import parse_email
from email_handler.email_threading import build_conversations


def refresh_inbox(client, limit: int, offset: int = 0, refresh: bool = False,
                   store=None, folder: str = "INBOX", sync_source: str = "page") -> dict:
    # Fetch one inbox page and save it when a store is provided.
    try:
        page = client.fetch_inbox(
            folder=folder, limit=limit, offset=offset, refresh=refresh
        )
        parsed = [parse_email(item["raw"], uid=item["uid"]) for item in page["emails"]]
        result = {
            "success": True,
            "emails": parsed,
            "conversations": conversations,
            "total": page["total"],
            "has_more": page["has_more"],
        }
        if store is not None and parsed:
            try:
                store.save_page(folder, parsed, source=sync_source)
            except Exception as store_error:
                result["store_error"] = str(store_error)
        return result
    except Exception as error:
        return {"success": False, "error": str(error)}


def load_cached_inbox(store, limit: int, offset: int = 0,
                      folder: str = "INBOX") -> dict:
    """Load a page directly from SQLite; no IMAP request is made."""
    try:
        page = store.get_page(folder, limit=limit, offset=offset)
        return {"success": True, **page}
    except Exception as error:
        return {"success": False, "error": str(error)}


def get_full_email(client, uid: str, folder: str = "INBOX", store=None) -> dict:
    """Return a cached full message when available; otherwise fetch it once."""
    try:
        if store is not None:
            cached = store.get_email(folder, uid)
            if cached and cached.get("is_full"):
                cached["attachments"] = store.get_attachments(folder, uid)
                return {"success": True, "email": cached}

        raw = client.fetch_single(folder, uid)
        if not raw:
            return {
                "success": False,
                "error": "Message not found (it may have been deleted).",
            }
        parsed = parse_email(raw, uid=uid)
        result = {"success": True, "email": parsed}
        if store is not None:
            try:
                store.save_full(folder, parsed)
            except Exception as store_error:
                result["store_error"] = str(store_error)
        return result
    except Exception as error:
        return {"success": False, "error": str(error)}


# Search saved emails for the current account.
def search_inbox(store, query: str, folder: str = "INBOX",
                  limit: int = 200) -> dict:
    try:
        result = store.search_emails(folder, query, limit=limit)
        return {"success": True, **result}
    except Exception as error:
        return {"success": False, "error": str(error)}


def sync_all_inbox(client, store, folder: str = "INBOX", page_size: int = 100,
                    progress_callback=None) -> dict:
    # Save the full inbox once and record sync progress.
    offset = 0
    synced = 0
    total = 0
    store.mark_sync_started(folder)

    while True:
        result = refresh_inbox(
            client,
            limit=page_size,
            offset=offset,
            refresh=(offset == 0),
            store=store,
            folder=folder,
            sync_source="full_sync",
        )
        if not result["success"]:
            store.mark_sync_failed(folder, result["error"], synced)
            return {
                "success": False,
                "error": result["error"],
                "synced": synced,
                "total": total,
            }

        total = result["total"]
        batch_count = len(result["emails"])
        synced += batch_count
        if progress_callback is not None:
            progress_callback(synced, total)

        if not result["has_more"] or batch_count == 0:
            break
        offset += batch_count

    store.mark_sync_complete(folder, total, synced)
    return {"success": True, "synced": synced, "total": total}
