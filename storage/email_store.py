import os
import sqlite3
from typing import Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emails.db")


class EmailStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
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
                is_read INTEGER DEFAULT 0,
                synced_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (folder, uid)
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_folder_date ON emails(folder, date DESC)"
        )

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                folder TEXT NOT NULL,
                uid TEXT NOT NULL,
                filename TEXT,
                content_type TEXT,
                size INTEGER,
                data BLOB
            )
        """)

        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_attachments_email ON attachments(folder, uid)"
        )

        self.conn.commit()

    # ---------------- writes ----------------

    def save_page(self, folder: str, parsed_emails: List[Dict], source: str = "page"):

        rows = [
            (
                folder, e["uid"], e.get("subject", ""), e.get("from", ""),
                e.get("to", ""), e.get("date", ""), e.get("date_display", ""),
                e.get("snippet", ""),
            )
            for e in parsed_emails
        ]
        self.conn.executemany("""
            INSERT INTO emails (folder, uid, subject, sender, recipient, date, date_display, snippet, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(folder, uid) DO UPDATE SET
                subject=excluded.subject,
                sender=excluded.sender,
                recipient=excluded.recipient,
                date=excluded.date,
                date_display=excluded.date_display,
                snippet=excluded.snippet,
                synced_at=excluded.synced_at
        """, rows)
        self.conn.commit()
        print(f"[email_store] save_page[{source}]: committed {len(rows)} row(s) "
              f"to '{self.db_path}' (folder='{folder}').", flush=True)

    def save_full(self, folder: str, parsed_email: Dict):

        e = parsed_email
        self.conn.execute("""
            INSERT INTO emails (
                folder, uid, subject, sender, recipient, date, date_display,
                snippet, body_text, body_html, is_full, is_read, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, datetime('now'))
            ON CONFLICT(folder, uid) DO UPDATE SET
                subject=excluded.subject,
                sender=excluded.sender,
                recipient=excluded.recipient,
                date=excluded.date,
                date_display=excluded.date_display,
                snippet=excluded.snippet,
                body_text=excluded.body_text,
                body_html=excluded.body_html,
                is_full=1,
                is_read=1,
                synced_at=excluded.synced_at
        """, (
            folder, e["uid"], e.get("subject", ""), e.get("from", ""),
            e.get("to", ""), e.get("date", ""), e.get("date_display", ""),
            e.get("snippet", ""), e.get("body_text", ""), e.get("body_html", ""),
        ))
        self.conn.commit()
        print(f"[email_store] save_full: committed full message "
              f"to '{self.db_path}' (folder='{folder}', uid={e['uid']}).", flush=True)
        
        if e.get("attachments"):
            self.save_attachments(folder, e["uid"], e["attachments"])

    def save_attachments(self, folder: str, uid: str, attachments: List[Dict]):
        self.conn.execute("DELETE FROM attachments WHERE folder=? AND uid=?", (folder, uid))
        rows = [
            (folder, uid, a.get("filename", ""), a.get("content_type", ""),
             a.get("size", 0), a.get("data"))
            for a in attachments
        ]
        if rows:
            self.conn.executemany("""
                INSERT INTO attachments (folder, uid, filename, content_type, size, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, rows)
        self.conn.commit()

    def get_attachments(self, folder: str, uid: str) -> List[Dict]:
        rows = self.conn.execute("""
            SELECT filename, content_type, size, data
            FROM attachments
            WHERE folder=? AND uid=?
        """, (folder, uid)).fetchall()
        return [dict(r) for r in rows]

    # ---------------- reads (offline-safe: local file only) ----------------

    def get_page(self, folder: str, limit: int = 50, offset: int = 0) -> Dict:
        total = self.conn.execute(
            "SELECT COUNT(*) FROM emails WHERE folder=?", (folder,)
        ).fetchone()[0]

        rows = self.conn.execute("""
            SELECT uid, subject, sender, recipient, date, date_display, snippet, is_full, is_read
            FROM emails
            WHERE folder=?
            ORDER BY date DESC
            LIMIT ? OFFSET ?
        """, (folder, limit, offset)).fetchall()

        return {
            "emails": [dict(r) for r in rows],
            "total": total,
            "has_more": offset + limit < total,
        }
    
    def search_emails(self, folder: str, query: str, limit: int = 100) -> Dict:
        like = f"%{query}%"
        rows = self.conn.execute("""
            SELECT uid, subject, sender AS "from", recipient, date, date_display, snippet, is_full, is_read
            FROM emails
            WHERE folder=? AND (subject LIKE ? OR sender LIKE ?)
            ORDER BY date DESC
            LIMIT ?
        """, (folder, like, like, limit)).fetchall()

        return {"emails": [dict(r) for r in rows], "total": len(rows)}

    def get_email(self, folder: str, uid: str) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM emails WHERE folder=? AND uid=?", (folder, uid)
        ).fetchone()
        return dict(row) if row else None

    def mark_read(self, folder: str, uid: str):
        self.conn.execute(
            "UPDATE emails SET is_read=1 WHERE folder=? AND uid=?", (folder, uid)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
