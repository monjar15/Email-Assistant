"""Microsoft Graph mailbox client with the interface used by the existing app."""
from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from email.policy import default as default_policy
from email.utils import format_datetime, formataddr
from threading import RLock
from typing import Dict, List, Optional
from urllib.parse import quote

import requests


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_TIMEOUT_SECONDS = 30
GRAPH_PREFER_HEADER = 'IdType="ImmutableId"'


class GraphMailClient:
    """Read one signed-in Outlook Inbox through delegated Microsoft Graph."""

    def __init__(self, token_provider):
        self.token_provider = token_provider
        self.email_address = ""
        self._profile: Dict = {}
        self._inbox_folder_id = ""
        self._lock = RLock()
        self._page_size: Optional[int] = None
        self._page_url_by_offset: Dict[int, Optional[str]] = {0: None}
        self._page_cache: Dict[int, Dict] = {}
        self._seen_uids: List[str] = []
        self._seen_uid_set = set()
        self._uid_snapshot_complete = False

    def connect(self) -> Dict:
        profile = self._request_json(
            "GET",
            "/me",
            params={"$select": "displayName,mail,userPrincipalName"},
        )
        self._profile = profile
        self.email_address = str(
            profile.get("mail") or profile.get("userPrincipalName") or ""
        ).strip()
        self._load_inbox_folder()
        return dict(profile)

    def disconnect(self):
        with self._lock:
            self._profile = {}
            self._inbox_folder_id = ""
            self._reset_pagination()

    def reconnect(self):
        self.connect()

    def ensure_connection(self):
        self.token_provider.get_access_token()
        if not self._inbox_folder_id:
            self._load_inbox_folder()

    def get_message_count(self, folder: str = "INBOX") -> Optional[int]:
        try:
            self.ensure_connection()
            data = self._request_json(
                "GET",
                "/me/mailFolders/inbox",
                params={"$select": "id,totalItemCount"},
            )
            folder_id = str(data.get("id") or "")
            if folder_id:
                self._inbox_folder_id = folder_id
            return int(data.get("totalItemCount") or 0)
        except Exception:
            return None

    def fetch_inbox(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        offset: int = 0,
        refresh: bool = False,
    ) -> Dict:
        self._require_inbox(folder)
        self.ensure_connection()
        limit = max(1, min(int(limit or 50), 250))
        offset = max(int(offset or 0), 0)

        with self._lock:
            if refresh or self._page_size != limit:
                self._page_size = limit
                self._reset_pagination()

            if offset in self._page_cache:
                return dict(self._page_cache[offset])

            self._materialize_until_offset(offset, limit)
            result = self._fetch_page(offset, limit)
            self._page_cache[offset] = result
            return dict(result)

    def list_uids(self, folder: str = "INBOX", refresh: bool = True) -> List[str]:
        self._require_inbox(folder)
        self.ensure_connection()

        with self._lock:
            if not refresh and self._uid_snapshot_complete:
                return list(self._seen_uids)
            if self._uid_snapshot_complete:
                return list(self._seen_uids)

        url = "/me/mailFolders/inbox/messages"
        params = {
            "$top": "250",
            "$select": "id",
            "$orderby": "receivedDateTime desc",
        }
        remote_uids: List[str] = []
        while url:
            data = self._request_json("GET", url, params=params)
            params = None
            for item in data.get("value", []):
                uid = str(item.get("id") or "")
                if uid:
                    remote_uids.append(uid)
            url = str(data.get("@odata.nextLink") or "")

        with self._lock:
            self._seen_uids = list(remote_uids)
            self._seen_uid_set = set(remote_uids)
            self._uid_snapshot_complete = True
        return remote_uids

    def uid_exists(self, folder: str, uid: str) -> bool:
        self._require_inbox(folder)
        self.ensure_connection()
        encoded_uid = quote(str(uid), safe="")
        data = self._request_json(
            "GET",
            f"/me/messages/{encoded_uid}",
            params={"$select": "id,parentFolderId"},
            allow_not_found=True,
        )
        if data is None:
            return False
        self._load_inbox_folder()
        return str(data.get("parentFolderId") or "") == self._inbox_folder_id

    def fetch_single(self, folder: str, uid: str) -> Optional[bytes]:
        self._require_inbox(folder)
        self.ensure_connection()
        encoded_uid = quote(str(uid), safe="")
        response = self.request_raw(
            "GET",
            f"/me/messages/{encoded_uid}/$value",
            allow_not_found=True,
        )
        if response is None:
            return None
        return bytes(response.content)

    def request_raw(
        self,
        method: str,
        path_or_url: str,
        *,
        params=None,
        allow_not_found: bool = False,
    ):
        url = self._absolute_url(path_or_url)
        response = self._send(method, url, params=params)
        if response.status_code == 404 and allow_not_found:
            return None
        if response.status_code >= 400:
            raise ConnectionError(self._graph_error(response))
        return response

    def _request_json(
        self,
        method: str,
        path_or_url: str,
        *,
        params=None,
        allow_not_found: bool = False,
    ):
        response = self.request_raw(
            method,
            path_or_url,
            params=params,
            allow_not_found=allow_not_found,
        )
        if response is None:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise ConnectionError("Microsoft Graph returned an invalid response.") from error

    def _send(self, method: str, url: str, *, params=None):
        token = self.token_provider.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Prefer": GRAPH_PREFER_HEADER,
        }
        try:
            response = requests.request(
                method,
                url,
                params=params,
                headers=headers,
                timeout=GRAPH_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise ConnectionError(f"Could not reach Microsoft Graph: {error}") from error

        if response.status_code == 401:
            token = self.token_provider.get_access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = requests.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=GRAPH_TIMEOUT_SECONDS,
                )
            except requests.RequestException as error:
                raise ConnectionError(f"Could not reach Microsoft Graph: {error}") from error
        return response

    def _load_inbox_folder(self):
        if self._inbox_folder_id:
            return
        data = self._request_json(
            "GET",
            "/me/mailFolders/inbox",
            params={"$select": "id"},
        )
        self._inbox_folder_id = str(data.get("id") or "")
        if not self._inbox_folder_id:
            raise ConnectionError("Microsoft Graph could not identify the Inbox folder.")

    def _reset_pagination(self):
        self._page_url_by_offset = {0: None}
        self._page_cache = {}
        self._seen_uids = []
        self._seen_uid_set = set()
        self._uid_snapshot_complete = False

    def _materialize_until_offset(self, target_offset: int, limit: int):
        while target_offset not in self._page_url_by_offset:
            candidates = [value for value in self._page_url_by_offset if value < target_offset]
            if not candidates:
                raise ValueError("Could not locate the requested Microsoft Graph page.")
            start = max(candidates)
            if start not in self._page_cache:
                self._page_cache[start] = self._fetch_page(start, limit)
            result = self._page_cache[start]
            next_offset = start + len(result.get("emails", []))
            if not result.get("has_more") or next_offset <= start:
                raise ValueError("The requested inbox page is no longer available.")
            if next_offset > target_offset:
                raise ValueError("Microsoft Graph returned an unexpected page boundary.")

    def _fetch_page(self, offset: int, limit: int) -> Dict:
        page_url = self._page_url_by_offset.get(offset)
        params = None
        if offset == 0 and not page_url:
            page_url = "/me/mailFolders/inbox/messages"
            params = {
                "$top": str(limit),
                "$select": (
                    "id,subject,from,toRecipients,receivedDateTime,"
                    "internetMessageId,bodyPreview"
                ),
                "$orderby": "receivedDateTime desc",
            }
        if not page_url:
            return {"emails": [], "total": self.get_message_count() or 0, "has_more": False}

        data = self._request_json("GET", page_url, params=params)
        items = list(data.get("value", []))
        emails = []
        for item in items:
            uid = str(item.get("id") or "")
            if not uid:
                continue
            emails.append({"uid": uid, "raw": self._header_message_bytes(item)})
            if uid not in self._seen_uid_set:
                self._seen_uid_set.add(uid)
                self._seen_uids.append(uid)

        next_link = str(data.get("@odata.nextLink") or "")
        next_offset = offset + len(emails)
        if next_link and next_offset > offset:
            self._page_url_by_offset[next_offset] = next_link
        elif not next_link:
            self._uid_snapshot_complete = offset == 0 or bool(self._seen_uids)

        return {
            "emails": emails,
            "total": self.get_message_count() or len(self._seen_uids),
            "has_more": bool(next_link),
        }

    @staticmethod
    def _header_message_bytes(item: Dict) -> bytes:
        message = EmailMessage(policy=default_policy)
        message["Subject"] = str(item.get("subject") or "(No Subject)")

        sender = (item.get("from") or {}).get("emailAddress") or {}
        sender_address = str(sender.get("address") or "")
        sender_name = str(sender.get("name") or "")
        message["From"] = formataddr((sender_name, sender_address)) if sender_address else sender_name

        recipients = []
        for recipient in item.get("toRecipients") or []:
            email_address = (recipient or {}).get("emailAddress") or {}
            address = str(email_address.get("address") or "")
            name = str(email_address.get("name") or "")
            if address:
                recipients.append(formataddr((name, address)))
            elif name:
                recipients.append(name)
        if recipients:
            message["To"] = ", ".join(recipients)

        received = GraphMailClient._parse_graph_datetime(item.get("receivedDateTime"))
        if received is not None:
            message["Date"] = format_datetime(received)

        internet_message_id = str(item.get("internetMessageId") or "").strip()
        if internet_message_id:
            message["Message-ID"] = internet_message_id

        message.set_content(str(item.get("bodyPreview") or ""))
        return message.as_bytes()

    @staticmethod
    def _parse_graph_datetime(value) -> Optional[datetime]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _absolute_url(path_or_url: str) -> str:
        value = str(path_or_url or "")
        if value.startswith(("https://", "http://")):
            return value
        if not value.startswith("/"):
            value = "/" + value
        return GRAPH_BASE_URL + value

    @staticmethod
    def _graph_error(response) -> str:
        try:
            payload = response.json()
            error = payload.get("error") or {}
            code = str(error.get("code") or "")
            message = str(error.get("message") or "")
            detail = ": ".join(part for part in (code, message) if part)
        except Exception:
            detail = str(response.text or "").strip()
        if response.status_code == 403:
            return (
                "Microsoft Graph denied mailbox access. Confirm that delegated "
                "Mail.Read is configured and approve the permission during sign-in."
            )
        return detail or f"Microsoft Graph request failed with HTTP {response.status_code}."

    @staticmethod
    def _require_inbox(folder: str):
        if str(folder or "INBOX").upper() != "INBOX":
            raise ValueError("This Microsoft Graph client currently supports the Inbox only.")
