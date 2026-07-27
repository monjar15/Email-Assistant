import os
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emails.db")

_FILTER_RE = re.compile(r'(?i)(?:^|\s)(from|to|subject):(?:"([^"]*)"|(\S+))')


def normalize_account_email(email_address: str) -> str:
    # Normalize the email address used as the account key.
    return (email_address or "").strip().casefold()


def _normalize_unicode(value) -> str:
    # Normalize text for search matching.
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _search_tokens(value) -> List[str]:
    # Split normalized text into search words.
    return re.findall(r"[a-z0-9]+", _normalize_unicode(value))


def _query_units(query) -> List[Tuple[str, str]]:
    # Build flexible search units without joining unrelated words.
    tokens = _search_tokens(query)
    units: List[Tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if len(token) == 1 and i + 1 < len(tokens):
            units.append(("compact", token + tokens[i + 1]))
            i += 2
        else:
            units.append(("word", token))
            i += 1
    return units


# Match compact search text against saved words.
def _compact_unit_matches(field_tokens: List[str], compact: str) -> bool:
    if not compact:
        return False

    if any(compact in token for token in field_tokens):
        return True

    for left, right in zip(field_tokens, field_tokens[1:]):
        if len(left) == 1 or len(right) == 1:
            if compact in (left + right):
                return True
    return False


# Check whether the query matches the selected fields.
def _search_matches_fields(query, values) -> int:
    field_token_lists = [_search_tokens(value) for value in values]
    all_tokens = [token for tokens in field_token_lists for token in tokens]
    units = _query_units(query)
    if not units:
        return 0

    for kind, value in units:
        if kind == "word":
            if any(value in token for token in all_tokens):
                continue
            if any(_compact_unit_matches(tokens, value) for tokens in field_token_lists):
                continue
            return 0

        if not any(_compact_unit_matches(tokens, value) for tokens in field_token_lists):
            return 0

    return 1


# Expose single-field matching to SQLite.
def _search_matches(value, query) -> int:
    return _search_matches_fields(query, [value])


# Expose full email matching to SQLite.
def _search_matches_email(subject, sender, recipient, snippet, body_text, query) -> int:
    return _search_matches_fields(
        query, [subject, sender, recipient, snippet, body_text]
    )


# Store email data in one database while keeping accounts isolated.
class EmailStore:
    # Open the database for one signed-in account.
    def __init__(self, account_email: str, db_path: str = DB_PATH):
        self.account_email = normalize_account_email(account_email)
        if not self.account_email or "@" not in self.account_email:
            raise ValueError("A valid signed-in email address is required for EmailStore.")

        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._backup_legacy_mixed_database_if_needed()

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.create_function(
            "SEARCH_MATCH", 2, _search_matches, deterministic=True
        )
        self.conn.create_function(
            "SEARCH_MATCH_EMAIL", 6, _search_matches_email, deterministic=True
        )
        self._init_db()
        self.account_id = self._get_or_create_account_id()

    def _backup_legacy_mixed_database_if_needed(self):
        # Back up an old database that has no account ownership.
        if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0:
            return

        probe = None
        try:
            probe = sqlite3.connect(self.db_path)
            tables = {
                row[0]
                for row in probe.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "emails" not in tables:
                return
            email_columns = {
                row[1] for row in probe.execute("PRAGMA table_info(emails)").fetchall()
            }
            if "account_id" in email_columns:
                return
        except sqlite3.DatabaseError:
            return
        finally:
            if probe is not None:
                probe.close()

        base_dir = os.path.dirname(os.path.abspath(self.db_path))
        base_name = os.path.join(base_dir, "emails_legacy_mixed_backup.db")
        backup_path = base_name
        if os.path.exists(backup_path):
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = os.path.join(
                base_dir, f"emails_legacy_mixed_backup_{stamp}.db"
            )

        shutil.move(self.db_path, backup_path)
        print(
            "[email_store] Legacy mixed database moved to "
            f"'{backup_path}'. A clean account-aware database will be created.",
            flush=True,
        )

    # Create the account-aware database tables.
    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_address TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now')),
                last_login_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS emails (
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
                synced_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (account_id, folder, uid),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_emails_account_folder_date
                ON emails(account_id, folder, date DESC);
            CREATE INDEX IF NOT EXISTS idx_emails_account_folder_sender
                ON emails(account_id, folder, sender);
            CREATE INDEX IF NOT EXISTS idx_emails_account_folder_recipient
                ON emails(account_id, folder, recipient);
            CREATE INDEX IF NOT EXISTS idx_emails_account_folder_subject
                ON emails(account_id, folder, subject);

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                folder TEXT NOT NULL,
                uid TEXT NOT NULL,
                filename TEXT,
                content_type TEXT,
                size INTEGER,
                data BLOB,
                FOREIGN KEY (account_id, folder, uid)
                    REFERENCES emails(account_id, folder, uid)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_attachments_account_email
                ON attachments(account_id, folder, uid);

            CREATE TABLE IF NOT EXISTS sync_state (
                account_id INTEGER NOT NULL,
                folder TEXT NOT NULL,
                full_sync_complete INTEGER DEFAULT 0,
                remote_total INTEGER DEFAULT 0,
                synced_count INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (account_id, folder),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
        """)
        self.conn.commit()

    # Load or create the current account record.
    def _get_or_create_account_id(self) -> int:
        self.conn.execute(
            """
            INSERT INTO accounts (email_address, last_login_at)
            VALUES (?, datetime('now'))
            ON CONFLICT(email_address) DO UPDATE SET
                last_login_at=datetime('now')
            """,
            (self.account_email,),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM accounts WHERE email_address=?",
            (self.account_email,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Could not create or load the signed-in account record.")
        return int(row["id"])

    # Convert one database row to the UI format.
    @staticmethod
    def _row_to_email(row: sqlite3.Row) -> Dict:
        data = dict(row)
        data.pop("account_id", None)
        if "sender" in data:
            data["from"] = data.pop("sender")
        if "recipient" in data:
            data["to"] = data.pop("recipient")
        return data

    # Return the saved email count for this account.
    def get_count(self, folder: str = "INBOX") -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM emails WHERE account_id=? AND folder=?",
            (self.account_id, folder),
        ).fetchone()[0]

    # Write operations.

    # Save or update one page of email headers.
    def save_page(self, folder: str, parsed_emails: List[Dict], source: str = "page") -> int:
        if not parsed_emails:
            return 0

        rows = [
            (
                self.account_id,
                folder,
                str(e["uid"]),
                e.get("subject", ""),
                e.get("from", ""),
                e.get("to", ""),
                e.get("date", ""),
                e.get("date_display", ""),
                e.get("snippet", ""),
            )
            for e in parsed_emails
        ]
        before_changes = self.conn.total_changes
        self.conn.executemany("""
            INSERT INTO emails (
                account_id, folder, uid, subject, sender, recipient, date,
                date_display, snippet, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(account_id, folder, uid) DO UPDATE SET
                subject=excluded.subject,
                sender=excluded.sender,
                recipient=excluded.recipient,
                date=excluded.date,
                date_display=excluded.date_display,
                snippet=CASE
                    WHEN excluded.snippet <> '' THEN excluded.snippet
                    ELSE emails.snippet
                END,
                synced_at=excluded.synced_at
            WHERE
                emails.subject IS NOT excluded.subject OR
                emails.sender IS NOT excluded.sender OR
                emails.recipient IS NOT excluded.recipient OR
                emails.date IS NOT excluded.date OR
                emails.date_display IS NOT excluded.date_display OR
                (excluded.snippet <> '' AND emails.snippet IS NOT excluded.snippet)
        """, rows)
        self.conn.commit()
        changed_rows = self.conn.total_changes - before_changes
        return changed_rows

    # Save the full body and attachments for one email.
    def save_full(self, folder: str, parsed_email: Dict):
        e = parsed_email
        uid = str(e["uid"])
        self.conn.execute("""
            INSERT INTO emails (
                account_id, folder, uid, subject, sender, recipient, date,
                date_display, snippet, body_text, body_html, is_full, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
            ON CONFLICT(account_id, folder, uid) DO UPDATE SET
                subject=excluded.subject,
                sender=excluded.sender,
                recipient=excluded.recipient,
                date=excluded.date,
                date_display=excluded.date_display,
                snippet=excluded.snippet,
                body_text=excluded.body_text,
                body_html=excluded.body_html,
                is_full=1,
                synced_at=excluded.synced_at
        """, (
            self.account_id,
            folder,
            uid,
            e.get("subject", ""),
            e.get("from", ""),
            e.get("to", ""),
            e.get("date", ""),
            e.get("date_display", ""),
            e.get("snippet", ""),
            e.get("body_text", ""),
            e.get("body_html", ""),
        ))
        self.conn.commit()

        if e.get("attachments"):
            self.save_attachments(folder, uid, e["attachments"])

    # Replace the saved attachments for one email.
    def save_attachments(self, folder: str, uid: str, attachments: List[Dict]):
        uid = str(uid)
        self.conn.execute(
            """
            DELETE FROM attachments
            WHERE account_id=? AND folder=? AND uid=?
            """,
            (self.account_id, folder, uid),
        )
        rows = [
            (
                self.account_id,
                folder,
                uid,
                a.get("filename", ""),
                a.get("content_type", ""),
                a.get("size", 0),
                a.get("data"),
            )
            for a in attachments
        ]
        if rows:
            self.conn.executemany("""
                INSERT INTO attachments (
                    account_id, folder, uid, filename, content_type, size, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, rows)
        self.conn.commit()

    # Record that the first full sync has started.
    def mark_sync_started(self, folder: str = "INBOX"):
        self.conn.execute("""
            INSERT INTO sync_state (
                account_id, folder, full_sync_complete, remote_total,
                synced_count, last_error, updated_at
            ) VALUES (?, ?, 0, 0, 0, NULL, datetime('now'))
            ON CONFLICT(account_id, folder) DO UPDATE SET
                full_sync_complete=0,
                synced_count=0,
                last_error=NULL,
                updated_at=datetime('now')
        """, (self.account_id, folder))
        self.conn.commit()

    # Record a completed full mailbox sync.
    def mark_sync_complete(self, folder: str, remote_total: int, synced_count: int):
        self.conn.execute("""
            INSERT INTO sync_state (
                account_id, folder, full_sync_complete, remote_total,
                synced_count, last_error, updated_at
            ) VALUES (?, ?, 1, ?, ?, NULL, datetime('now'))
            ON CONFLICT(account_id, folder) DO UPDATE SET
                full_sync_complete=1,
                remote_total=excluded.remote_total,
                synced_count=excluded.synced_count,
                last_error=NULL,
                updated_at=datetime('now')
        """, (self.account_id, folder, remote_total or 0, synced_count or 0))
        self.conn.commit()

    # Record a failed full mailbox sync.
    def mark_sync_failed(self, folder: str, error: str, synced_count: int = 0):
        self.conn.execute("""
            INSERT INTO sync_state (
                account_id, folder, full_sync_complete, synced_count,
                last_error, updated_at
            ) VALUES (?, ?, 0, ?, ?, datetime('now'))
            ON CONFLICT(account_id, folder) DO UPDATE SET
                full_sync_complete=0,
                synced_count=excluded.synced_count,
                last_error=excluded.last_error,
                updated_at=datetime('now')
        """, (self.account_id, folder, synced_count, error))
        self.conn.commit()

    # Update the latest remote mailbox count.
    def update_remote_total(self, folder: str, remote_total: int):
        self.conn.execute("""
            INSERT INTO sync_state (account_id, folder, remote_total, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(account_id, folder) DO UPDATE SET
                remote_total=excluded.remote_total,
                updated_at=datetime('now')
        """, (self.account_id, folder, remote_total or 0))
        self.conn.commit()

    # Read operations.

    # Load one saved inbox page for this account.
    def get_page(self, folder: str, limit: int = 50, offset: int = 0) -> Dict:
        total = self.get_count(folder)
        rows = self.conn.execute("""
            SELECT
                uid, subject, sender, recipient, date, date_display, snippet,
                is_full
            FROM emails
            WHERE account_id=? AND folder=?
            ORDER BY date DESC, CAST(uid AS INTEGER) DESC
            LIMIT ? OFFSET ?
        """, (self.account_id, folder, limit, offset)).fetchall()
        return {
            "emails": [self._row_to_email(r) for r in rows],
            "total": total,
            "has_more": offset + len(rows) < total,
        }

    # Split field filters from the search text.
    def _parse_search_query(self, query: str) -> Tuple[List[Tuple[str, str]], str]:
        filters: List[Tuple[str, str]] = []

        # Collect one field filter from the query.
        def capture(match):
            field = match.group(1).lower()
            value = match.group(2) if match.group(2) is not None else match.group(3)
            if value and value.strip():
                filters.append((field, value.strip()))
            return " "

        remaining = _FILTER_RE.sub(capture, query or "")
        return filters, " ".join(remaining.split())

    # Search saved emails for this account.
    def search_emails(self, folder: str, query: str, limit: int = 100) -> Dict:
        query = (query or "").strip()
        if not query:
            return {"emails": [], "total": 0}

        filters, general_query = self._parse_search_query(query)
        if not filters and not _query_units(general_query):
            return {"emails": [], "total": 0}

        conditions = ["account_id=?", "folder=?"]
        params: List[object] = [self.account_id, folder]

        field_map = {
            "from": "sender",
            "to": "recipient",
            "subject": "subject",
        }
        for field, value in filters:
            if _query_units(value):
                conditions.append(
                    f"SEARCH_MATCH(COALESCE({field_map[field]}, ''), ?) = 1"
                )
                params.append(value)

        if general_query and _query_units(general_query):
            conditions.append("""
                SEARCH_MATCH_EMAIL(
                    COALESCE(subject, ''),
                    COALESCE(sender, ''),
                    COALESCE(recipient, ''),
                    COALESCE(snippet, ''),
                    COALESCE(body_text, ''),
                    ?
                ) = 1
            """)
            params.append(general_query)

        where_sql = " AND ".join(conditions)
        total = self.conn.execute(
            f"SELECT COUNT(*) FROM emails WHERE {where_sql}", params
        ).fetchone()[0]
        rows = self.conn.execute(f"""
            SELECT
                uid, subject, sender, recipient, date, date_display, snippet,
                is_full
            FROM emails
            WHERE {where_sql}
            ORDER BY date DESC, CAST(uid AS INTEGER) DESC
            LIMIT ?
        """, [*params, limit]).fetchall()

        return {
            "emails": [self._row_to_email(r) for r in rows],
            "total": total,
        }

    # Load one saved email by folder and UID.
    def get_email(self, folder: str, uid: str) -> Optional[Dict]:
        row = self.conn.execute(
            """
            SELECT * FROM emails
            WHERE account_id=? AND folder=? AND uid=?
            """,
            (self.account_id, folder, str(uid)),
        ).fetchone()
        return self._row_to_email(row) if row else None

    # Load saved attachments for one email.
    def get_attachments(self, folder: str, uid: str) -> List[Dict]:
        rows = self.conn.execute("""
            SELECT filename, content_type, size, data
            FROM attachments
            WHERE account_id=? AND folder=? AND uid=?
        """, (self.account_id, folder, str(uid))).fetchall()
        return [dict(r) for r in rows]

    # Load the saved sync state for one folder.
    def get_sync_state(self, folder: str = "INBOX") -> Optional[Dict]:
        row = self.conn.execute(
            """
            SELECT folder, full_sync_complete, remote_total, synced_count,
                   last_error, updated_at
            FROM sync_state
            WHERE account_id=? AND folder=?
            """,
            (self.account_id, folder),
        ).fetchone()
        return dict(row) if row else None

    # Close the SQLite connection.
    def close(self):
        self.conn.close()
