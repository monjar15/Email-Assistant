import imaplib
import re
import ssl
from typing import Dict, List, Optional


RECONNECTABLE_IMAP_ERRORS = (
    ssl.SSLEOFError,
    imaplib.IMAP4.abort,
    imaplib.IMAP4.error,
    OSError,
)


# Handle IMAP connections and message fetching.
class IMAPClient:
    # Store connection settings and initialize caches.
    def __init__(self, server: str, port: int, email_address: str, password: str):
        self.server = server
        self.port = port
        self.email_address = email_address
        self.password = password
        self.conn: Optional[imaplib.IMAP4_SSL] = None

        self._known_total: Optional[int] = None
        self._uid_list_folder: Optional[str] = None
        self._uid_list: List[bytes] = []
        self._page_cache: Dict[int, Dict] = {}

    # Open and authenticate the IMAP connection.
    def connect(self) -> bool:
        new_conn = None
        try:
            new_conn = imaplib.IMAP4_SSL(self.server, self.port)
            new_conn.login(self.email_address, self.password)
            self.conn = new_conn
            return True
        except imaplib.IMAP4.error as error:
            self._close_connection(new_conn)
            self.conn = None
            raise ConnectionError(f"IMAP login failed: {error}")
        except Exception as error:
            self._close_connection(new_conn)
            self.conn = None
            raise ConnectionError(f"Could not connect to {self.server}: {error}")

    # Close one IMAP socket safely, including partially authenticated sockets.
    @staticmethod
    def _close_connection(conn):
        if conn is None:
            return
        try:
            sock = getattr(conn, "sock", None)
            if sock is not None:
                sock.settimeout(2.0)
            state = str(getattr(conn, "state", "")).upper()
            if state in {"AUTH", "SELECTED"}:
                conn.logout()
            else:
                conn.shutdown()
        except Exception:
            try:
                conn.shutdown()
            except Exception:
                try:
                    sock = getattr(conn, "sock", None)
                    if sock is not None:
                        sock.close()
                except Exception:
                    pass

    # Close the IMAP connection without delaying logout.
    def disconnect(self):
        conn = self.conn
        self.conn = None
        self._close_connection(conn)

        self._known_total = None
        self._uid_list_folder = None
        self._uid_list = []
        self._page_cache = {}

    # Reconnect after the current connection is lost.
    def reconnect(self):
        self.disconnect()
        self.connect()

    # Select a folder and return its current message count.
    def _select_folder(self, folder: str) -> int:
        status, select_data = self.conn.select(folder)
        if status != "OK":
            raise ValueError(f"Could not open folder: {folder}")
        try:
            return int(select_data[0])
        except (TypeError, ValueError, IndexError):
            return 0

    # Load stable IMAP UIDs for the selected folder.
    def _load_uid_list(self, folder: str, refresh: bool = False) -> List[bytes]:
        total = self._select_folder(folder)
        should_reload = (
            refresh
            or self._uid_list_folder != folder
            or self._known_total != total
            or not self._uid_list
        )
        if should_reload:
            status, data = self.conn.uid("search", None, "ALL")
            if status != "OK":
                raise ValueError(f"Could not read message UIDs from folder: {folder}")
            raw_ids = data[0] if data and data[0] else b""
            self._uid_list = [item for item in raw_ids.split() if item.isdigit()]
            self._uid_list_folder = folder
            self._known_total = len(self._uid_list)
            self._page_cache = {}
        return list(self._uid_list)

    # Return all stable IMAP UIDs without downloading message content.
    def list_uids(self, folder: str = "INBOX", refresh: bool = True) -> List[str]:
        self.ensure_connection()
        try:
            uid_list = self._load_uid_list(folder, refresh=refresh)
        except RECONNECTABLE_IMAP_ERRORS:
            self.reconnect()
            uid_list = self._load_uid_list(folder, refresh=True)
        return [uid.decode("ascii", errors="ignore") for uid in uid_list]

    # Check whether one stable UID still exists in the selected folder.
    def uid_exists(self, folder: str, uid: str) -> bool:
        self.ensure_connection()

        def _check() -> bool:
            self._select_folder(folder)
            status, data = self.conn.uid("search", None, "UID", str(uid))
            if status != "OK":
                raise ValueError("Could not validate the selected email.")
            found = data[0].split() if data and data[0] else []
            return str(uid).encode("ascii", errors="ignore") in found

        try:
            return _check()
        except RECONNECTABLE_IMAP_ERRORS:
            self.reconnect()
            return _check()

    # Fetch one header-only page from an IMAP folder.
    def fetch_inbox(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        offset: int = 0,
        refresh: bool = False,
    ) -> Dict:
        self.ensure_connection()

        try:
            uid_list = self._load_uid_list(folder, refresh=refresh)
            if not refresh and offset in self._page_cache:
                return self._page_cache[offset]
            header_by_uid, page_uids, total, start = self._fetch_uid_page(
                uid_list, limit, offset
            )
        except RECONNECTABLE_IMAP_ERRORS:
            self.reconnect()
            uid_list = self._load_uid_list(folder, refresh=True)
            header_by_uid, page_uids, total, start = self._fetch_uid_page(
                uid_list, limit, offset
            )

        emails = []
        for uid in page_uids:
            raw = header_by_uid.get(uid)
            if raw:
                emails.append({"uid": uid.decode(), "raw": raw})

        result = {
            "emails": emails,
            "total": total,
            "has_more": start > 0,
        }
        self._page_cache[offset] = result
        return result

    # Slice one page from the UID list and fetch its headers.
    def _fetch_uid_page(self, uid_list: List[bytes], limit: int, offset: int):
        total = len(uid_list)
        end = total - offset
        if end <= 0:
            return {}, [], total, 0

        start = max(0, end - limit) if limit else 0
        page_uids = list(reversed(uid_list[start:end]))
        header_by_uid = self._fetch_headers_batch(page_uids)
        return header_by_uid, page_uids, total, start

    # Return the current message count for a folder.
    def get_message_count(self, folder: str = "INBOX") -> Optional[int]:
        # This is a background poll, so a temporary authentication or network
        # failure must not crash the whole Streamlit page.
        try:
            self.ensure_connection()
            status, data = self.conn.status(folder, "(MESSAGES)")
        except (ConnectionError, *RECONNECTABLE_IMAP_ERRORS):
            try:
                self.reconnect()
                status, data = self.conn.status(folder, "(MESSAGES)")
            except (ConnectionError, *RECONNECTABLE_IMAP_ERRORS):
                return None

        if status != "OK" or not data or not data[0]:
            return None

        match = re.search(rb"MESSAGES (\d+)", data[0])
        return int(match.group(1)) if match else None

    # Fetch one full raw email from a folder by stable IMAP UID.
    def fetch_single(self, folder: str, uid: str) -> Optional[bytes]:
        self.ensure_connection()

        try:
            self._select_folder(folder)
            return self._fetch_raw(str(uid).encode())
        except RECONNECTABLE_IMAP_ERRORS:
            self.reconnect()
            self._select_folder(folder)
            return self._fetch_raw(str(uid).encode())

    # Fetch raw content for one stable IMAP UID.
    def _fetch_raw(self, uid: bytes) -> Optional[bytes]:
        status, msg_data = self.conn.uid("fetch", uid, "(RFC822)")
        if status != "OK":
            return None
        for part in msg_data:
            if isinstance(part, tuple):
                return part[1]
        return None

    # Fetch headers for a group of stable IMAP UIDs.
    def _fetch_headers_batch(self, uids: List[bytes]) -> Dict[bytes, bytes]:
        return self._fetch_batch(
            uids,
            "(UID BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE MESSAGE-ID)])",
        )

    # Run one UID batch fetch and map results by stable UID.
    def _fetch_batch(self, uids: List[bytes], fetch_item: str) -> Dict[bytes, bytes]:
        if not uids:
            return {}

        uid_set = b",".join(uids)
        status, msg_data = self.conn.uid("fetch", uid_set, fetch_item)
        if status != "OK":
            return {}

        results: Dict[bytes, bytes] = {}
        for part in msg_data:
            if not isinstance(part, tuple):
                continue
            response_header, raw = part[0], part[1]
            match = re.search(rb"\bUID (\d+)\b", response_header)
            if match:
                results[match.group(1)] = raw
        return results

    # Check the connection before an IMAP request.
    def ensure_connection(self):
        if not self.conn:
            self.connect()
            return

        state = str(getattr(self.conn, "state", "")).upper()
        if state not in {"AUTH", "SELECTED"}:
            self.reconnect()
            return

        try:
            self.conn.noop()
        except RECONNECTABLE_IMAP_ERRORS:
            self.reconnect()
