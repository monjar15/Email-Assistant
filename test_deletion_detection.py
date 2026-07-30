import os
import sqlite3
import tempfile
import unittest

from services.deletion_detection_service import (
    check_uid_availability,
    reconcile_folder,
)
from storage.email_store import EmailStore


def _email(uid: str, subject: str) -> dict:
    return {
        "uid": uid,
        "subject": subject,
        "from": "sender@example.com",
        "to": "owner@example.com",
        "date": "2026-07-30T00:00:00+00:00",
        "date_display": "2026-07-30",
        "snippet": subject,
    }


class FakeClient:
    def __init__(self, remote_uids=None, error=None):
        self.remote_uids = list(remote_uids or [])
        self.error = error

    def list_uids(self, folder, refresh=True):
        if self.error:
            raise self.error
        return list(self.remote_uids)

    def uid_exists(self, folder, uid):
        if self.error:
            raise self.error
        return str(uid) in self.remote_uids


class DeletionDetectionTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.store = EmailStore("owner@example.com", db_path=self.db_path)
        self.store.save_page(
            "INBOX",
            [_email("101", "Keep"), _email("102", "Deleted elsewhere")],
        )

    def tearDown(self):
        self.store.close()
        for suffix in ("", "-shm", "-wal"):
            try:
                os.remove(self.db_path + suffix)
            except FileNotFoundError:
                pass

    def test_reconciliation_hides_only_missing_uid(self):
        result = reconcile_folder(
            FakeClient(remote_uids=["101"]),
            self.store,
            "INBOX",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.missing_uids, ["102"])
        self.assertEqual(self.store.get_active_uids("INBOX"), {"101"})
        self.assertIsNone(self.store.get_email("INBOX", "102"))
        self.assertIsNotNone(
            self.store.get_email("INBOX", "102", include_unavailable=True)
        )

    def test_reconciliation_restores_reappearing_uid(self):
        self.store.mark_remote_unavailable("INBOX", ["102"])
        result = reconcile_folder(
            FakeClient(remote_uids=["101", "102"]),
            self.store,
            "INBOX",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.missing_uids, [])
        self.assertEqual(self.store.get_active_uids("INBOX"), {"101", "102"})

    def test_network_failure_is_not_treated_as_deletion(self):
        result = reconcile_folder(
            FakeClient(error=ConnectionError("offline")),
            self.store,
            "INBOX",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.missing_uids, [])
        self.assertEqual(self.store.get_active_uids("INBOX"), {"101", "102"})

    def test_single_uid_check_distinguishes_absence_from_failure(self):
        missing = check_uid_availability(
            FakeClient(remote_uids=["101"]), "102", "INBOX"
        )
        failed = check_uid_availability(
            FakeClient(error=ConnectionError("offline")), "102", "INBOX"
        )

        self.assertEqual(
            missing,
            {"success": True, "available": False, "error": ""},
        )
        self.assertFalse(failed["success"])
        self.assertIsNone(failed["available"])

    def test_legacy_sequence_number_cache_is_rebuilt_once(self):
        self.store.close()
        os.remove(self.db_path)
        connection = sqlite3.connect(self.db_path)
        connection.executescript(
            """
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY,
                email_address TEXT NOT NULL UNIQUE,
                created_at TEXT,
                last_login_at TEXT
            );
            INSERT INTO accounts (id, email_address)
            VALUES (1, 'owner@example.com');
            CREATE TABLE emails (
                account_id INTEGER NOT NULL,
                folder TEXT NOT NULL,
                uid TEXT NOT NULL,
                subject TEXT,
                sender TEXT,
                recipient TEXT,
                date TEXT,
                date_display TEXT,
                snippet TEXT,
                body_text TEXT,
                body_html TEXT,
                is_full INTEGER DEFAULT 0,
                synced_at TEXT,
                PRIMARY KEY (account_id, folder, uid)
            );
            INSERT INTO emails (account_id, folder, uid, subject)
            VALUES (1, 'INBOX', '1', 'Mutable sequence number');
            """
        )
        connection.commit()
        connection.close()

        self.store = EmailStore("owner@example.com", db_path=self.db_path)

        self.assertTrue(self.store.cache_identifier_migrated)
        self.assertEqual(self.store.get_count("INBOX"), 0)
        mode = self.store.conn.execute(
            "SELECT value FROM app_meta WHERE key='email_identifier_mode'"
        ).fetchone()[0]
        self.assertEqual(mode, "imap_uid_v1")


if __name__ == "__main__":
    unittest.main()
