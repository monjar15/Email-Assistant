# Email service: fetch + parse orchestration for the inbox.
from email_handler.email_parser import parse_email


def refresh_inbox(client, limit: int, offset: int = 0, refresh: bool = False,
                   store=None, folder: str = "INBOX", sync_source: str = "page") -> dict:
    # Fetch one page of the inbox (headers only) via the given
    # IMAPClient and parse each into a dict for the list view.

    try:
        page = client.fetch_inbox(folder=folder, limit=limit, offset=offset, refresh=refresh)
        parsed = [parse_email(raw["raw"], uid=raw["uid"]) for raw in page["emails"]]
        result = {
            "success": True,
            "emails": parsed,
            "total": page["total"],
            "has_more": page["has_more"],
        }
        if store is not None:
            try:
                store.save_page(folder, parsed, source=sync_source)
            except Exception as store_e:
                result["store_error"] = str(store_e)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_full_email(client, uid: str, folder: str = "INBOX", store=None) -> dict:
    # Fetch and parse the FULL message (including body) for one email,
    # on demand — called when the user opens/selects an email in the list,
    # since the list itself only ever has headers (see refresh_inbox).

    try:
        raw = client.fetch_single(folder, uid)
        if not raw:
            return {"success": False, "error": "Message not found (it may have been deleted)."}
        parsed = parse_email(raw, uid=uid)
        result = {"success": True, "email": parsed}
        if store is not None:
            try:
                store.save_full(folder, parsed)
            except Exception as store_e:
                result["store_error"] = str(store_e)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    
def search_inbox(store, query: str, folder: str = "INBOX", limit: int = 100) -> dict:

    try:
        result = store.search_emails(folder, query, limit=limit)
        return {"success": True, "emails": result["emails"], "total": result["total"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sync_all_inbox(client, store, folder: str = "INBOX", page_size: int = 100,
                    progress_callback=None) -> dict:
    # Page through the ENTIRE mailbox (not just one page) and save
    # every message header to `store` via repeated refresh_inbox() calls.

    offset = 0
    synced = 0
    total = None
    while True:
        result = refresh_inbox(
            client, limit=page_size, offset=offset, refresh=(offset == 0),
            store=store, folder=folder, sync_source="full_sync",
        )
        if not result["success"]:
            return {"success": False, "error": result["error"], "synced": synced, "total": total}

        total = result["total"]
        synced += len(result["emails"])
        if progress_callback is not None:
            progress_callback(synced, total)

        if not result["has_more"] or not result["emails"]:
            break
        offset += page_size

    return {"success": True, "synced": synced, "total": total}
