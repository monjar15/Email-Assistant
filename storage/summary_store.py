"""Persistent, account-isolated SQLite storage for generated AI summaries."""
import json
import os
import sqlite3


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "summaries.db")


class SummaryStore:
    """Store the current generated summary set for one signed-in account."""

    def __init__(self, account_email: str, db_path: str = DB_PATH):
        self.account_email = (account_email or "").strip().casefold()
        if not self.account_email:
            raise ValueError("A signed-in email address is required for SummaryStore.")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                account_email TEXT NOT NULL,
                folder TEXT NOT NULL,
                uid TEXT NOT NULL,
                sender TEXT,
                recipient TEXT,
                subject TEXT,
                date_value TEXT,
                date_display TEXT,
                snippet TEXT,
                summary TEXT NOT NULL,
                key_points TEXT NOT NULL,
                deadlines TEXT NOT NULL,
                action_items TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Pending',
                is_read INTEGER NOT NULL DEFAULT 0,
                generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (account_email, folder, uid)
            )
        """)
        columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(summaries)")
        }
        if "priority" not in columns:
            self.conn.execute(
                "ALTER TABLE summaries ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium'"
            )
        if "status" not in columns:
            self.conn.execute(
                "ALTER TABLE summaries ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'"
            )
        if "is_read" not in columns:
            self.conn.execute(
                "ALTER TABLE summaries ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0"
            )
        self.conn.commit()

    def append_all(self, folder: str, summaries: list[dict]):
        """Save new summaries without removing earlier summaries in the folder."""
        with self.conn:
            self.conn.executemany("""
                INSERT INTO summaries (
                    account_email, folder, uid, sender, recipient, subject,
                    date_value, date_display, snippet, summary, key_points,
                    deadlines, action_items, priority, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    self.account_email, folder, str(item.get("uid", "")),
                    item.get("from", ""), item.get("to", ""),
                    item.get("subject", ""), item.get("date", ""),
                    item.get("date_display", ""), item.get("snippet", ""),
                    item.get("summary", ""), json.dumps(item.get("key_points", [])),
                    json.dumps(item.get("deadlines", [])),
                    json.dumps(item.get("action_items", [])),
                    item.get("priority", "Medium"),
                    item.get("status", "Pending"),
                ) for item in summaries
            ])

    def get_uids(self, folder: str) -> set[str]:
        """Return existing summary IDs so callers can prevent duplicates."""
        rows = self.conn.execute(
            "SELECT uid FROM summaries WHERE account_email=? AND folder=?",
            (self.account_email, folder),
        ).fetchall()
        return {str(row["uid"]) for row in rows}

    def update_status(self, folder: str, uid: str, status: str):
        """Persist a task summary status for future To-Do integration."""
        normalized = str(status or "Pending").strip().casefold()
        allowed = {
            "complete": "Complete",
            "completed": "Complete",
            "in progress": "In Progress",
            "pending": "Pending",
        }
        value = allowed.get(normalized, "Pending")
        with self.conn:
            self.conn.execute(
                "UPDATE summaries SET status=? WHERE account_email=? AND folder=? AND uid=?",
                (value, self.account_email, folder, str(uid)),
            )

    def mark_read(self, folder: str, uid: str):
        """Mark one opened summary as read."""
        with self.conn:
            self.conn.execute(
                "UPDATE summaries SET is_read=1 WHERE account_email=? AND folder=? AND uid=?",
                (self.account_email, folder, str(uid)),
            )

    def load_all(self, folder: str) -> list[dict]:
        """Load saved summaries in their most recently generated order."""
        rows = self.conn.execute("""
            SELECT uid, sender, recipient, subject, date_value, date_display,
                   snippet, summary, key_points, deadlines, action_items,
                   priority, status, is_read
            FROM summaries
            WHERE account_email=? AND folder=?
            ORDER BY generated_at DESC, rowid DESC
        """, (self.account_email, folder)).fetchall()
        return [{
            "uid": row["uid"], "from": row["sender"], "to": row["recipient"],
            "subject": row["subject"], "date": row["date_value"],
            "date_display": row["date_display"], "snippet": row["snippet"],
            "summary": row["summary"],
            "priority": row["priority"], "status": row["status"],
            "is_read": bool(row["is_read"]),
            "key_points": json.loads(row["key_points"]),
            "deadlines": json.loads(row["deadlines"]),
            "action_items": json.loads(row["action_items"]),
        } for row in rows]

    def close(self):
        self.conn.close()
