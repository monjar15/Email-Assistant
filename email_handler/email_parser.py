import base64
import email as stdlib_email
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Dict, Optional


def _decode(value: Optional[str]) -> str:
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = ""
    for text, encoding in decoded_parts:
        if isinstance(text, bytes):
            result += text.decode(encoding or "utf-8", errors="ignore")
        else:
            result += text
    return result


def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _sanitize_html(html: str) -> str:

    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<noscript[^>]*>.*?</noscript>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'\son\w+\s*=\s*"[^"]*"', "", html, flags=re.IGNORECASE)
    html = re.sub(r"\son\w+\s*=\s*'[^']*'", "", html, flags=re.IGNORECASE)
    html = re.sub(r'(href|src)\s*=\s*"javascript:[^"]*"', r'\1="#"', html, flags=re.IGNORECASE)
    html = re.sub(r"(href|src)\s*=\s*'javascript:[^']*'", r"\1='#'", html, flags=re.IGNORECASE)

    html = re.sub(
        r"<img ",
        '<img onerror="this.style.display=\'none\'" referrerpolicy="no-referrer" '
        'style="max-width:100%;height:auto;" ',
        html,
        flags=re.IGNORECASE,
    )
    return html

def _resolve_inline_images(html: str, cid_images: Dict[str, tuple]) -> str:

    for cid_key, (content_type, payload) in cid_images.items():
        b64 = base64.b64encode(payload).decode("ascii")
        data_uri = f"data:{content_type};base64,{b64}"
        html = html.replace(f"cid:{cid_key}", data_uri)
    return html

def parse_email(raw_bytes: bytes, uid: str = "") -> Dict:
    """Parse a raw RFC822 message into a structured dict."""
    msg = stdlib_email.message_from_bytes(raw_bytes)

    subject = _decode(msg.get("Subject"))
    from_addr = _decode(msg.get("From"))
    to_addr = _decode(msg.get("To"))
    date_str = msg.get("Date")

    message_id = (msg.get("Message-ID") or "").strip()
    in_reply_to = (msg.get("In-Reply-To") or "").strip()
    references = [r for r in (msg.get("References") or "").split() if r]

    try:
        date_obj = parsedate_to_datetime(date_str) if date_str else None
    except (TypeError, ValueError):
        date_obj = None

    body_text = ""
    body_html = ""
    attachments = []
    cid_images: Dict[str, tuple] = {}  # content-id -> (content_type, raw bytes)

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            filename = part.get_filename()
            content_id = part.get("Content-ID")

            if content_id and content_type.startswith("image/"):
                try:
                    payload = part.get_payload(decode=True)
                except Exception:
                    payload = None
                if payload:
                    cid_images[content_id.strip("<>")] = (content_type, payload)
                continue

            if "attachment" in disposition or filename:
                try:
                    payload = part.get_payload(decode=True)
                except Exception:
                    payload = None
                if payload and filename:
                    attachments.append({
                        "filename": _decode(filename),
                        "content_type": content_type,
                        "size": len(payload),
                        "data": payload,
                    })
                continue

            try:
                payload = part.get_payload(decode=True)
            except Exception:
                payload = None
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="ignore")
            if content_type == "text/plain" and not body_text:
                body_text = decoded
            elif content_type == "text/html" and not body_html:
                body_html = decoded
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="ignore") if payload else ""
        except Exception:
            decoded = msg.get_payload() or ""
        if msg.get_content_type() == "text/html":
            body_html = decoded
        else:
            body_text = decoded

    if not body_text and body_html:
        body_text = _strip_html(body_html)

    if body_html:
        if cid_images:
            body_html = _resolve_inline_images(body_html, cid_images)
        body_html = _sanitize_html(body_html)

    snippet_source = body_text.strip()
    snippet = (snippet_source[:150] + "...") if len(snippet_source) > 150 else snippet_source

    return {
        "uid": uid,
        "subject": subject or "(No Subject)",
        "from": from_addr,
        "to": to_addr,
        "date": date_obj.isoformat() if date_obj else "",
        "date_display": date_obj.strftime("%Y-%m-%d %H:%M") if date_obj else "Unknown",
        "body_text": body_text.strip(),
        "body_html": body_html,
        "snippet": snippet,
        "attachments": attachments,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
    }
