import base64
import concurrent.futures
import functools
import html as html_lib
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parseaddr

import streamlit as st
import streamlit.components.v1 as components


READER_HEIGHT = 720  # CSS adjusts this fallback height.
MAX_REMOTE_IMAGES = 28
MAX_IMAGE_BYTES = 6 * 1024 * 1024
IMAGE_TIMEOUT_SECONDS = 4

_AVATAR_CLASS_COUNT = 8


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent urllib from following redirects before we validate the next URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _sender_avatar(sender: str):
    name, address = parseaddr(sender or "")
    label = (name or address or sender or "?").strip().strip('"')
    initial = (label[:1] or "?").upper()
    tone_index = sum(ord(ch) for ch in (sender or "")) % _AVATAR_CLASS_COUNT
    return initial, f"avatar-tone-{tone_index}"


def _sender_markup(sender: str) -> str:
    name, address = parseaddr(sender or "")
    if name and address:
        return (
            f'<span class="reader-sender-name">{html_lib.escape(name)}</span>'
            f'<span class="reader-sender-address"> &lt;{html_lib.escape(address)}&gt;</span>'
        )
    return (
        '<span class="reader-sender-name">'
        f'{html_lib.escape(address or sender or "Unknown sender")}</span>'
    )


_FILE_TYPE_STYLES = {
    "pdf": ("PDF", "pdf"),
    "doc": ("DOC", "doc"), "docx": ("DOC", "doc"),
    "xls": ("XLS", "xls"), "xlsx": ("XLS", "xls"), "csv": ("CSV", "xls"),
    "ppt": ("PPT", "ppt"), "pptx": ("PPT", "ppt"),
    "zip": ("ZIP", "file"), "rar": ("RAR", "file"), "7z": ("7Z", "file"),
    "png": ("IMG", "img"), "jpg": ("IMG", "img"),
    "jpeg": ("IMG", "img"), "gif": ("IMG", "img"),
    "txt": ("TXT", "file"),
}


def _file_type_badge(filename: str):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _FILE_TYPE_STYLES.get(ext, ((ext.upper()[:4] or "FILE"), "file"))


def _safe_download_filename(name: str, fallback: str) -> str:
    name = name or fallback
    cleaned = re.sub(r'[\\/*?:"<>|\r\n]', "_", name)
    cleaned = cleaned.encode("ascii", errors="ignore").decode("ascii").strip(" ._")
    return cleaned or fallback


def _format_file_size(size: int) -> str:
    try:
        value = float(size or 0)
    except (TypeError, ValueError):
        value = 0
    units = ["B", "KB", "MB", "GB"]
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"


def _remove_dark_mode_media_blocks(content: str) -> str:
    """Remove CSS dark-mode media blocks while keeping normal email CSS intact."""
    result = content
    search_from = 0
    while True:
        match = re.search(r"@media\s*[^\{]*prefers-color-scheme\s*:\s*dark[^\{]*\{", result[search_from:], re.I)
        if not match:
            break
        start = search_from + match.start()
        open_brace = search_from + match.end() - 1
        depth = 0
        end = None
        for index in range(open_brace, len(result)):
            char = result[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            result = result[:start]
            break
        result = result[:start] + result[end:]
        search_from = start
    return result


def _is_public_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                return False
        return True
    except (OSError, ValueError):
        return False


@functools.lru_cache(maxsize=512)
def _fetch_image_as_data_uri(url: str) -> str | None:
    """Fetch a public remote image and convert it to a data URI for reliable previewing."""
    current_url = html_lib.unescape(url.strip())
    opener = urllib.request.build_opener(_NoRedirectHandler())

    for _ in range(4):
        if not _is_public_http_url(current_url):
            return None

        request = urllib.request.Request(
            current_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"
                ),
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            },
        )

        try:
            response = opener.open(request, timeout=IMAGE_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as error:
            if error.code in {301, 302, 303, 307, 308}:
                location = error.headers.get("Location")
                if not location:
                    return None
                current_url = urllib.parse.urljoin(current_url, location)
                continue
            return None
        except (OSError, urllib.error.URLError, TimeoutError):
            return None

        with response:
            content_type = (response.headers.get_content_type() or "").lower()
            payload = response.read(MAX_IMAGE_BYTES + 1)
            if len(payload) > MAX_IMAGE_BYTES or not payload:
                return None
            if not content_type.startswith("image/"):
                return None
            encoded = base64.b64encode(payload).decode("ascii")
            return f"data:{content_type};base64,{encoded}"

    return None


def _embed_remote_images(content: str) -> str:
    """Proxy common remote IMG sources so they render like Gmail/Outlook image proxies."""
    pattern = re.compile(r"(<img\b[^>]*?\bsrc\s*=\s*)([\"'])(https?://.*?)(\2)", re.I | re.S)
    urls = []
    seen = set()
    for match in pattern.finditer(content):
        url = html_lib.unescape(match.group(3).strip())
        if url not in seen:
            seen.add(url)
            urls.append(url)
        if len(urls) >= MAX_REMOTE_IMAGES:
            break

    if not urls:
        return content

    replacements: dict[str, str] = {}
    workers = min(8, len(urls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(_fetch_image_as_data_uri, url): url for url in urls}
        for future, url in [(future, future_map[future]) for future in future_map]:
            try:
                data_uri = future.result()
            except Exception:
                data_uri = None
            if data_uri:
                replacements[url] = data_uri

    if not replacements:
        return content

    def replace_source(match: re.Match) -> str:
        original = html_lib.unescape(match.group(3).strip())
        replacement = replacements.get(original)
        if not replacement:
            return match.group(0)
        return f"{match.group(1)}{match.group(2)}{replacement}{match.group(4)}"

    return pattern.sub(replace_source, content)


# Remove unsafe wrappers while preserving the original email visual formatting.
def _prepare_html_fragment(raw_html: str) -> str:
    content = (raw_html or "").strip()
    if not content:
        return ""

    if "&lt;" in content and not re.search(r"<\s*(html|body|table|div|p|style)\b", content, re.I):
        content = html_lib.unescape(content)

    content = re.sub(r"<!doctype[^>]*>", "", content, flags=re.I)
    content = re.sub(r"<script\b[^>]*>.*?</script>", "", content, flags=re.I | re.S)
    content = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", content, flags=re.I | re.S)
    content = re.sub(r"<(object|embed|form)\b[^>]*>.*?</\1>", "", content, flags=re.I | re.S)
    content = re.sub(r"<meta\b[^>]*(color-scheme|supported-color-schemes)[^>]*>", "", content, flags=re.I)
    content = re.sub(r"<meta\b[^>]*http-equiv\s*=\s*['\"]?refresh['\"]?[^>]*>", "", content, flags=re.I)
    content = re.sub(r"\s+on\w+\s*=\s*(['\"]).*?\1", "", content, flags=re.I | re.S)
    content = re.sub(r"\s+on\w+\s*=\s*[^\s>]+", "", content, flags=re.I)
    content = re.sub(r"(href|src)\s*=\s*(['\"])\s*javascript:.*?\2", r'\1="#"', content, flags=re.I | re.S)
    content = re.sub(r"@import\s+[^;]+;", "", content, flags=re.I)
    content = _remove_dark_mode_media_blocks(content)

    # Convert protocol-relative asset URLs so icons/images can render correctly.
    content = re.sub(r'(?i)(src|href)=("|\')//', r'\1=\2https://', content)

    styles = "".join(re.findall(r"<style\b[^>]*>.*?</style>", content, flags=re.I | re.S))
    body_match = re.search(r"<body\b[^>]*>(.*?)</body>", content, flags=re.I | re.S)
    if body_match:
        content = body_match.group(1)
    else:
        content = re.sub(r"</?(html|head|body)\b[^>]*>", "", content, flags=re.I)

    content = re.sub(
        r"<a\b(?![^>]*\btarget=)",
        '<a target="_blank" rel="noopener noreferrer" ',
        content,
        flags=re.I,
    )
    content = _embed_remote_images(content)
    return styles + content


# Build an isolated light-mode document that keeps original email dimensions.
def _build_html_document(raw_html: str) -> str:
    fragment = _prepare_html_fragment(raw_html)
    return (
        "<!doctype html>"
        '<html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light only">'
        '<meta name="supported-color-schemes" content="light">'
        '<base target="_blank">'
        "</head><body><div class='email-shell'><div class='email-canvas'>"
        + fragment
        + "</div></div></body></html>"
    )


# Estimate a useful embedded-preview height without breaking the workspace.
def _html_preview_height(raw_html: str, body_text: str) -> int:
    text = body_text or re.sub(r"<[^>]+>", " ", raw_html or "")
    text = re.sub(r"\s+", " ", text).strip()
    blocks = len(re.findall(r"<(p|div|tr|li|br|img|table)\b", raw_html or "", flags=re.I))
    wide_layout = bool(re.search(r"<(table|img)\b", raw_html or "", flags=re.I))
    estimated = 320 + min(380, len(text) // 7) + min(180, blocks * 4)
    if wide_layout:
        estimated += 90
    return max(420, min(860, estimated))


def render_reader(message):
    if not message:
        with st.container(height=READER_HEIGHT, border=False, key="reader_content_scroll"):
            st.markdown(
                """
                <div class="empty-state reader-empty-state">
                    <div class="reader-empty-inner">
                        <div class="reader-empty-icon" aria-hidden="true">
                            <svg viewBox="0 0 64 64" role="img">
                                <rect x="12" y="18" width="40" height="30" rx="4" fill="none" stroke="currentColor" stroke-width="3"/>
                                <path d="M14 22.5L29.3 35.2a4.2 4.2 0 0 0 5.4 0L50 22.5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <div class="reader-empty-copy">Select an email from the list to view it here.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return

    email_data = message["email"]
    attachments = message.get("attachments") or []
    sender = email_data.get("from", "")
    subject = email_data.get("subject") or "(No Subject)"
    date_display = email_data.get("date_display", "Unknown")
    initial, avatar_class = _sender_avatar(sender)

    header_html = (
        '<div class="reader-header reader-header-modern">'
        '<div class="reader-header-row">'
        f'<div class="reader-avatar reader-avatar-modern {avatar_class}">{html_lib.escape(initial)}</div>'
        '<div class="reader-title-stack">'
        f'<div class="reader-subject reader-subject-modern">{html_lib.escape(subject)}</div>'
        '<div class="reader-meta-line reader-meta-line-1">'
        f'<span class="reader-meta-pill"><span class="reader-meta-icon">✉</span>{_sender_markup(sender)}</span>'
        '</div>'
        '<div class="reader-meta-line reader-meta-line-2">'
        f'<span class="reader-meta-pill"><span class="reader-meta-icon">◷</span>{html_lib.escape(date_display)}</span>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
    )

    with st.container(border=False, key="reader_header"):
        st.markdown(header_html, unsafe_allow_html=True)

    with st.container(height=READER_HEIGHT, border=False, key="reader_content_scroll"):
        with st.container(border=False, key="reader_body_shell"):
            _render_message(email_data, attachments)


def _render_message(email_data, attachments=None):
    body_html = email_data.get("body_html") or ""
    body_text = email_data.get("body_text") or ""

    if body_html.strip():
        document = _build_html_document(body_html)
        components.html(document, height=_html_preview_height(body_html, body_text), scrolling=True)
    else:
        display_text = body_text or "(No text content)"
        st.markdown(
            '<div class="reader-body">'
            + html_lib.escape(display_text)
            + '</div>',
            unsafe_allow_html=True,
        )

    attachments = attachments or email_data.get("attachments") or []
    if not attachments:
        return

    st.markdown(
        '<div class="reader-section-label">'
        f'Attachments ({len(attachments)})</div>',
        unsafe_allow_html=True,
    )

    cards_html = []
    for index, attachment in enumerate(attachments):
        filename = attachment.get("filename") or f"attachment_{index + 1}"
        safe_filename_html = html_lib.escape(filename)
        safe_download_name = _safe_download_filename(filename, f"attachment_{index + 1}")
        file_bytes = attachment.get("data") or b""
        mime = attachment.get("content_type") or "application/octet-stream"
        b64 = base64.b64encode(file_bytes).decode("ascii") if file_bytes else ""
        href = f"data:{mime};base64,{b64}" if b64 else "#"
        label, badge_class = _file_type_badge(filename)
        size_label = _format_file_size(attachment.get("size", len(file_bytes)))
        cards_html.append(
            '<a '
            f'href="{href}" '
            f'download="{html_lib.escape(safe_download_name)}" '
            'class="attachment-card">'
            f'<span class="attachment-badge attachment-badge-{badge_class}">'
            f'{html_lib.escape(label)}</span>'
            '<span class="attachment-copy">'
            f'<span class="attachment-name">{safe_filename_html}</span>'
            f'<span class="attachment-size">{html_lib.escape(size_label)}</span>'
            '</span>'
            '<span aria-hidden="true" class="attachment-download-icon">⇩</span>'
            '</a>'
        )

    st.markdown(
        '<div class="attachment-grid">'
        + ''.join(cards_html)
        + '</div>',
        unsafe_allow_html=True,
    )
