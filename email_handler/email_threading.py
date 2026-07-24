import imaplib
import re
import ssl
from typing import Dict, List, Optional, Tuple

# Domains where Gmail's X-GM-THRID extension is available.
GMAIL_THREADING_DOMAINS = {"gmail.com", "googlemail.com"}


def get_domain(email_address: str) -> str:
    return email_address.rsplit("@", 1)[-1].strip().lower()


def supports_gmail_threading(email_address: str) -> bool:
    return get_domain(email_address) in GMAIL_THREADING_DOMAINS


_ALL_MAIL_CANDIDATES = ["[Gmail]/All Mail", "[Google Mail]/All Mail"]


def _find_all_mail_by_special_use(client) -> Optional[str]:

    try:
        status, folders = client.conn.list()
    except Exception:
        return None
    if status != "OK" or not folders:
        return None

    for f in folders:
        line = f.decode(errors="ignore") if isinstance(f, bytes) else str(f)
        m = re.match(r'^\(([^)]*)\)\s+"[^"]*"\s+(.+)$', line.strip())
        if not m:
            continue
        attrs, name = m.group(1), m.group(2).strip().strip('"')
        if "\\all" in attrs.lower():
            return name
    return None


def resolve_all_mail_folder(client) -> Optional[str]:

    by_attr = _find_all_mail_by_special_use(client)
    if by_attr:
        try:
            status, _ = client.conn.select(by_attr)
            if status == "OK":
                return by_attr
        except Exception:
            pass

    for name in _ALL_MAIL_CANDIDATES:
        try:
            status, _ = client.conn.select(name)
            if status == "OK":
                return name
        except Exception:
            continue
    return None


def build_conversations(client, emails: List[Dict], folder: str = "INBOX") -> List[Dict]:
 
    if not emails:
        return []

    if not supports_gmail_threading(client.email_address):
        return [_single_email_conversation(e) for e in emails]

    uids = [e["uid"] for e in emails if e.get("uid")]
    thread_by_uid = _fetch_thread_ids(client, folder, uids)

    if not thread_by_uid:
        return [_single_email_conversation(e) for e in emails]

    for e in emails:
        thrid = thread_by_uid.get(e.get("uid"))
        if thrid:
            e["thread_id"] = thrid

    groups: Dict[str, List[Dict]] = {}
    order: List[str] = []  # preserve first-seen (newest-first) order

    for e in emails:
        thrid = thread_by_uid.get(e["uid"])
        if thrid is None:
            # No thread id came back for this particular message — give
            # it its own group instead of silently dropping it.
            thrid = f"__single_{e['uid']}"
        if thrid not in groups:
            groups[thrid] = []
            order.append(thrid)
        groups[thrid].append(e)

    order, groups, root_members = _merge_linked_groups(emails, order, groups)
    _debug_log_unmerged_subject_collisions(order, groups)

    all_real_thread_ids = sorted({
        t for members in root_members.values() for t in members
        if not t.startswith("__single_")
    })
    full_uids_by_thread, all_mail_folder = _fetch_full_thread_uids(client, folder, all_real_thread_ids)

    conversations = []
    for root in order:
        member_thrids = [t for t in root_members[root] if not t.startswith("__single_")]
        union_uids: List[str] = []
        seen_uid = set()
        for t in member_thrids:
            for u in full_uids_by_thread.get(t, []):
                if u not in seen_uid:
                    seen_uid.add(u)
                    union_uids.append(u)
        conversations.append(_make_conversation(
            root, groups[root],
            union_uids or None,
            all_mail_folder if union_uids else None,
        ))
    return conversations


def _normalize_subject(subject: str) -> str:
    s = (subject or "").strip().lower()
    return re.sub(r"^((re|fwd?|fw)(\[\d+\])?\s*:\s*)+", "", s).strip()


def _debug_log_unmerged_subject_collisions(order: List[str], groups: Dict[str, List[Dict]]) -> None:
    by_subject: Dict[str, List[str]] = {}
    for root in order:
        subj = _normalize_subject(groups[root][0].get("subject"))
        by_subject.setdefault(subj, []).append(root)

    for subj, roots in by_subject.items():
        if len(roots) < 2 or not subj:
            continue
        print(f"[thread-debug] possible split thread, subject={subj!r}", flush=True)
        for root in roots:
            print(f"[thread-debug]   group root={root!r}", flush=True)
            for m in groups[root]:
                print(
                    f"[thread-debug]     uid={m.get('uid')!r} "
                    f"date={m.get('date')!r} from={m.get('from')!r} "
                    f"message_id={m.get('message_id')!r} "
                    f"in_reply_to={m.get('in_reply_to')!r} "
                    f"references={m.get('references')!r}",
                    flush=True,
                )


def _merge_linked_groups(emails: List[Dict], order: List[str], groups: Dict[str, List[Dict]]):
    parent = {k: k for k in order}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    group_of_uid: Dict[str, str] = {}
    for k, msgs in groups.items():
        for m in msgs:
            if m.get("uid"):
                group_of_uid[m["uid"]] = k

    msgid_to_group: Dict[str, str] = {}
    for m in emails:
        mid = (m.get("message_id") or "").strip()
        own_group = group_of_uid.get(m.get("uid"))
        if mid and own_group:
            msgid_to_group[mid] = own_group

    for m in emails:
        own_group = group_of_uid.get(m.get("uid"))
        if not own_group:
            continue
        linked_ids = []
        if m.get("in_reply_to"):
            linked_ids.append(m["in_reply_to"])
        linked_ids.extend(m.get("references") or [])
        for mid in linked_ids:
            other_group = msgid_to_group.get((mid or "").strip())
            if other_group and other_group != own_group:
                union(own_group, other_group)

    new_order: List[str] = []
    new_groups: Dict[str, List[Dict]] = {}
    root_members: Dict[str, List[str]] = {}
    for k in order:
        root = find(k)
        if root not in new_groups:
            new_groups[root] = []
            new_order.append(root)
            root_members[root] = []
        new_groups[root].extend(groups[k])
        root_members[root].append(k)

    # Messages were concatenated group-by-group above, so a merged
    # conversation's list may no longer be newest-first overall even
    # though each original group was — re-sort so `_make_conversation`
    # (which assumes msgs[0] is the newest) stays correct.
    for root in new_groups:
        new_groups[root].sort(key=lambda m: m.get("date") or "", reverse=True)

    return new_order, new_groups, root_members


def _single_email_conversation(e: Dict) -> Dict:
    uid = e.get("uid", "")
    return {
        "thread_id": uid,
        "subject": e.get("subject") or "(No Subject)",
        "emails": [e],
        "all_uids": [uid] if uid else [],
        "count": 1,
        "latest_date": e.get("date", ""),
        "latest_date_display": e.get("date_display", "Unknown"),
        "participants": [p for p in (e.get("from"),) if p],
        "is_thread": False,
        "all_mail_folder": None,
    }


def _make_conversation(thread_id: str, msgs: List[Dict], all_uids: List[str] = None,
                        all_mail_folder: str = None) -> Dict:
    # msgs keep the page's original order (newest-first); the newest
    # message represents the conversation in the list view.
    latest = msgs[0]

    participants = []
    seen = set()
    for m in msgs:
        frm = m.get("from")
        if frm and frm not in seen:
            seen.add(frm)
            participants.append(frm)

    if all_uids:
        resolved_folder = all_mail_folder
    else:
        all_uids = [m["uid"] for m in msgs if m.get("uid")]
        resolved_folder = None
    true_count = max(len(all_uids), len(msgs))

    return {
        "thread_id": thread_id,
        "subject": latest.get("subject") or "(No Subject)",
        "emails": msgs,
        "all_uids": all_uids,
        "count": true_count,
        "latest_date": latest.get("date", ""),
        "latest_date_display": latest.get("date_display", "Unknown"),
        "participants": participants,
        "is_thread": true_count > 1,
        "all_mail_folder": resolved_folder,
    }


def _fetch_thread_ids(client, folder: str, uids: List[str]) -> Dict[str, str]:
    if not uids:
        return {}

    client.ensure_connection()
    msg_ids = [u.encode() for u in uids]
    id_set = b",".join(msg_ids)

    try:
        status, _ = client.conn.select(folder)
        if status != "OK":
            return {}
        status, data = client.conn.fetch(id_set, "(X-GM-THRID)")
    except (ssl.SSLEOFError, imaplib.IMAP4.abort, OSError):
        try:
            client.reconnect()
            status, _ = client.conn.select(folder)
            if status != "OK":
                return {}
            status, data = client.conn.fetch(id_set, "(X-GM-THRID)")
        except Exception:
            return {}
    except imaplib.IMAP4.error:
        return {}

    if status != "OK" or not data:
        return {}

    thread_by_uid: Dict[str, str] = {}
    for part in data:
        if isinstance(part, tuple):
            raw = part[0]
        elif isinstance(part, bytes):
            raw = part
        else:
            continue

        text = raw.decode(errors="ignore")
        seq_match = re.match(r"(\d+)\s+", text)
        thrid_match = re.search(r"X-GM-THRID\s+(\d+)", text)
        if seq_match and thrid_match:
            thread_by_uid[seq_match.group(1)] = thrid_match.group(1)

    return thread_by_uid


def _fetch_full_thread_uids(client, folder: str, thread_ids: List[str]) -> Tuple[Dict[str, List[str]], Optional[str]]:
   
    if not thread_ids:
        return {}, None

    client.ensure_connection()
    result: Dict[str, List[str]] = {}

    try:
        all_mail_folder = resolve_all_mail_folder(client)
        if not all_mail_folder:
            return {}, None
    except (ssl.SSLEOFError, imaplib.IMAP4.abort, OSError):
        try:
            client.reconnect()
            all_mail_folder = resolve_all_mail_folder(client)
            if not all_mail_folder:
                return {}, None
        except Exception:
            return {}, None
    except imaplib.IMAP4.error:
        return {}, None

    for thrid in thread_ids:
        try:
            status, data = client.conn.search(None, f"X-GM-THRID {thrid}")
        except (ssl.SSLEOFError, imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError):
            continue
        if status != "OK" or not data or not data[0]:
            continue
        result[thrid] = data[0].decode(errors="ignore").split()

    try:
        client.conn.select(folder)
    except Exception:
        pass

    return result, all_mail_folder
