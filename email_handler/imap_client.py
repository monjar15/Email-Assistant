#IMAP client wrapper: handles connecting, listing folders, and fetching
#raw email messages from a mail server.

import ssl
import imaplib
import re
from typing import List, Dict, Optional


class IMAPClient:
    #Thin wrapper around imaplib for the email assistant's needs."""

    def __init__(self, server: str, port: int, email_address: str, password: str):
        self.server = server
        self.port = port
        self.email_address = email_address
        self.password = password
        self.conn: Optional[imaplib.IMAP4_SSL] = None

        self._known_total: Optional[int] = None
        self._id_list_folder: Optional[str] = None

        self._page_cache: Dict[int, Dict] = {}

    def connect(self) -> bool:
        #Open a connection and log in. Raises ConnectionError on failure."""
        try:
            self.conn = imaplib.IMAP4_SSL(self.server, self.port)
            self.conn.login(self.email_address, self.password)
            return True
        except imaplib.IMAP4.error as e:
            raise ConnectionError(f"IMAP login failed: {e}")
        except Exception as e:
            raise ConnectionError(f"Could not connect to {self.server}: {e}")

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
                self.conn.logout()
            except Exception:
                pass
            self.conn = None

        self._known_total = None
        self._id_list_folder = None
        self._page_cache = {}

    def reconnect(self):
        self.disconnect()
        self.connect()

    def list_folders(self) -> List[str]:
        self.ensure_connection()

        try:
            status, folders = self.conn.list()
        except (ssl.SSLEOFError, imaplib.IMAP4.abort, OSError):
            self.reconnect()
            status, folders = self.conn.list()

        result = []

        if status == "OK":
            for f in folders:
                parts = f.decode(errors="ignore").split('"')
                if len(parts) >= 3:
                    result.append(parts[-2].strip())
                else:
                    result.append(f.decode(errors="ignore"))

        return result

    def fetch_inbox(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        offset: int = 0,
        refresh: bool = False,
    ) -> Dict:
        # Fetch the most recent `limit` raw messages from `folder`.
        self.ensure_connection()

        try:
            status, select_data = self.conn.select(folder)
            if status != "OK":
                raise ValueError(f"Could not open folder: {folder}")

            # select_data[0] is the EXISTS count for this folder.
            try:
                total = int(select_data[0])
            except (TypeError, ValueError, IndexError):
                total = 0

            if refresh or self._id_list_folder != folder or self._known_total != total:
                self._page_cache = {}
                self._id_list_folder = folder
                self._known_total = total

            if not refresh and offset in self._page_cache:
                return self._page_cache[offset]

            end = total - offset
            if end <= 0:
                result = {"emails": [], "total": total, "has_more": False}
                self._page_cache[offset] = result
                return result

            start = max(0, end - limit) if limit else 0

            page_ids = [str(i).encode() for i in range(start + 1, end + 1)]
            page_ids.reverse()  # newest first

            header_by_id = self._fetch_headers_batch(page_ids)

        except (ssl.SSLEOFError, imaplib.IMAP4.abort, OSError):
            # Connection was lost while selecting/fetching.
            self.reconnect()

            status, select_data = self.conn.select(folder)
            if status != "OK":
                raise ValueError(f"Could not open folder: {folder}")

            try:
                total = int(select_data[0])
            except (TypeError, ValueError, IndexError):
                total = 0

            self._page_cache = {}
            self._id_list_folder = folder
            self._known_total = total

            end = total - offset
            if end <= 0:
                return {"emails": [], "total": total, "has_more": False}

            start = max(0, end - limit) if limit else 0

            page_ids = [str(i).encode() for i in range(start + 1, end + 1)]
            page_ids.reverse()

            header_by_id = self._fetch_headers_batch(page_ids)

        emails = []
        for msg_id in page_ids:
            raw = header_by_id.get(msg_id)
            if raw:
                emails.append(
                    {
                        "uid": msg_id.decode(),
                        "raw": raw,
                    }
                )

        result = {
            "emails": emails,
            "total": total,
            "has_more": start > 0,
        }

        self._page_cache[offset] = result
        return result
    
    def get_message_count(self, folder: str = "INBOX") -> Optional[int]:
        self.ensure_connection()

        try:
            status, data = self.conn.status(folder, "(MESSAGES)")
        except (ssl.SSLEOFError, imaplib.IMAP4.abort, OSError):
            self.reconnect()
            status, data = self.conn.status(folder, "(MESSAGES)")

        if status != "OK" or not data or not data[0]:
            return None

        match = re.search(rb"MESSAGES (\d+)", data[0])
        return int(match.group(1)) if match else None

    def fetch_single(self, folder: str, uid: str) -> Optional[bytes]:
        self.ensure_connection()

        try:
            status, _ = self.conn.select(folder)
            if status != "OK":
                return None
        
            return self._fetch_raw(uid.encode())

        except (ssl.SSLEOFError, imaplib.IMAP4.abort, OSError):
            self.reconnect()

            status, _ = self.conn.select(folder)
            if status != "OK":
                return None

            return self._fetch_raw(uid.encode())

    def _fetch_raw(self, msg_id: bytes) -> Optional[bytes]:
        status, msg_data = self.conn.fetch(msg_id, "(RFC822)")

        if status != "OK":
            return None

        for part in msg_data:
            if isinstance(part, tuple):
                return part[1]

        return None
    
    def _fetch_raw_batch(self, msg_ids: List[bytes]) -> Dict[bytes, bytes]:
        return self._fetch_batch(msg_ids, "(RFC822)")

    def _fetch_headers_batch(self, msg_ids: List[bytes]) -> Dict[bytes, bytes]:
        return self._fetch_batch(msg_ids, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE)])")

    def _fetch_batch(self, msg_ids: List[bytes], fetch_item: str) -> Dict[bytes, bytes]:
        if not msg_ids:
            return {}

        id_set = b",".join(msg_ids)

        status, msg_data = self.conn.fetch(id_set, fetch_item)
        if status != "OK":
            return {}

        results: Dict[bytes, bytes] = {}

        for part in msg_data:
            if not isinstance(part, tuple):
                continue

            header, raw = part[0], part[1]
            seq = header.split(b" ", 1)[0]

            if seq.isdigit():
                results[seq] = raw

        return results

    def ensure_connection(self):
        #Ensure that the IMAP connection is alive.
        if not self.conn:
            self.connect()
            return

        try:
            self.conn.noop()      
        except (ssl.SSLEOFError,
                imaplib.IMAP4.abort,
                OSError):
            self.reconnect()