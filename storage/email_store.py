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
                thread_id TEXT,
                message_id TEXT,
                in_reply_to TEXT,
                references_hdr TEXT,
                synced_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (folder, uid)
            )
        """)
        # Migrate DBs created before the threading columns existed —
        # ALTER TABLE ADD COLUMN is safe/additive, so existing rows just
        # get NULLs in the new columns until the next sync fills them in.
        existing_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(emails)")}
        for col in ("thread_id", "message_id", "in_reply_to", "references_hdr"):
            if col not in existing_cols:
                self.conn.execute(f"ALTER TABLE emails ADD COLUMN {col} TEXT")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_folder_date ON emails(folder, date DESC)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_folder_thread ON emails(folder, thread_id)"
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
                e.get("thread_id", ""), e.get("message_id", ""),
                e.get("in_reply_to", ""), " ".join(e.get("references") or []),
            )
            for e in parsed_emails
        ]
        self.conn.executemany("""
            INSERT INTO emails (
                folder, uid, subject, sender, recipient, date, date_display, snippet,
                thread_id, message_id, in_reply_to, references_hdr, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(folder, uid) DO UPDATE SET
                subject=excluded.subject,
                sender=excluded.sender,
                recipient=excluded.recipient,
                date=excluded.date,
                date_display=excluded.date_display,
                snippet=excluded.snippet,
                thread_id=excluded.thread_id,
                message_id=excluded.message_id,
                in_reply_to=excluded.in_reply_to,
                references_hdr=excluded.references_hdr,
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
                snippet, body_text, body_html, is_full, is_read,
                message_id, in_reply_to, references_hdr, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, datetime('now'))
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
                message_id=excluded.message_id,
                in_reply_to=excluded.in_reply_to,
                references_hdr=excluded.references_hdr,
                synced_at=excluded.synced_at
        """, (
            folder, e["uid"], e.get("subject", ""), e.get("from", ""),
            e.get("to", ""), e.get("date", ""), e.get("date_display", ""),
            e.get("snippet", ""), e.get("body_text", ""), e.get("body_html", ""),
            e.get("message_id", ""), e.get("in_reply_to", ""),
            " ".join(e.get("references") or []),
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

    def get_conversation_count(self, folder: str, gmail_threading: bool) -> int:

        total_rows = self.conn.execute(
            "SELECT COUNT(*) FROM emails WHERE folder=?", (folder,)
        ).fetchone()[0]

        if not gmail_threading:
            return total_rows

        rows = self.conn.execute("""
            SELECT uid, thread_id, message_id, in_reply_to, references_hdr
            FROM emails WHERE folder=?
        """, (folder,)).fetchall()

        # Group by X-GM-THRID (fall back to a singleton group for any
        # row a thread_id never got captured for — e.g. rows saved
        # before this column existed).
        group_of_uid: Dict[str, str] = {}
        groups: Dict[str, list] = {}
        for r in rows:
            key = r["thread_id"] or f"__single_{r['uid']}"
            group_of_uid[r["uid"]] = key
            groups.setdefault(key, []).append(r)

        # Union-find merge via In-Reply-To/References links — same
        # algorithm as email_threading._merge_linked_groups, just run
        # over the whole folder instead of one page.
        parent = {k: k for k in groups}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        msgid_to_group: Dict[str, str] = {}
        for r in rows:
            mid = (r["message_id"] or "").strip()
            if mid:
                msgid_to_group[mid] = group_of_uid[r["uid"]]

        for r in rows:
            own_group = group_of_uid[r["uid"]]
            linked_ids = []
            if r["in_reply_to"]:
                linked_ids.append(r["in_reply_to"])
            if r["references_hdr"]:
                linked_ids.extend(r["references_hdr"].split())
            for mid in linked_ids:
                other_group = msgid_to_group.get((mid or "").strip())
                if other_group and other_group != own_group:
                    union(own_group, other_group)

        return len({find(k) for k in groups})

    def close(self):
        self.conn.close()
