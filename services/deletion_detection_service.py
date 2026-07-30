"""Detect emails removed from an IMAP folder and persist their availability."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class ReconciliationResult:
    """Outcome of one complete remote/local UID comparison."""

    success: bool
    remote_uids: List[str] = field(default_factory=list)
    missing_uids: List[str] = field(default_factory=list)
    error: str = ""


def reconcile_folder(client, store, folder: str = "INBOX") -> ReconciliationResult:
    """Compare stable remote UIDs with the cache without downloading messages."""
    try:
        remote_uids = client.list_uids(folder, refresh=True)
        missing_uids = store.reconcile_remote_uids(folder, remote_uids)
        return ReconciliationResult(
            success=True,
            remote_uids=remote_uids,
            missing_uids=missing_uids,
        )
    except Exception as error:
        # A network failure must not be interpreted as mailbox deletion.
        return ReconciliationResult(success=False, error=str(error))


def check_uid_availability(client, uid: str, folder: str = "INBOX") -> dict:
    """Validate one stable UID while distinguishing failure from absence."""
    try:
        return {
            "success": True,
            "available": bool(client.uid_exists(folder, str(uid))),
            "error": "",
        }
    except Exception as error:
        return {"success": False, "available": None, "error": str(error)}
