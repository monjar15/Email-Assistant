import base64
import html as html_lib
import re

import streamlit as st
from ui.styles import COLORS


READER_HEIGHT = 720  # CSS adjusts this fallback height.

# Use a stable avatar color for each sender.
_AVATAR_COLORS = ["#C9A24B", "#1A73E8", "#188038", "#E37400", "#9334E6", "#D93025", "#12B5CB", "#7CB342"]


# Build a stable avatar for the sender.
def _sender_avatar(sender: str):
    name = (sender or "?").split("<", 1)[0].strip().strip('"')
    initial = (name[:1] or (sender[:1] if sender else "?")).upper()
    color = _AVATAR_COLORS[sum(ord(ch) for ch in (sender or "")) % len(_AVATAR_COLORS)]
    return initial, color


# Map file extensions to attachment badge labels and colors.
_FILE_TYPE_STYLES = {
    "pdf": ("PDF", "#EA4335"),
    "doc": ("DOC", "#1A73E8"), "docx": ("DOC", "#1A73E8"),
    "xls": ("XLS", "#188038"), "xlsx": ("XLS", "#188038"), "csv": ("CSV", "#188038"),
    "ppt": ("PPT", "#E37400"), "pptx": ("PPT", "#E37400"),
    "zip": ("ZIP", "#5F6368"), "rar": ("RAR", "#5F6368"), "7z": ("7Z", "#5F6368"),
    "png": ("IMG", "#9334E6"), "jpg": ("IMG", "#9334E6"), "jpeg": ("IMG", "#9334E6"), "gif": ("IMG", "#9334E6"),
    "txt": ("TXT", "#5F6368"),
}


# Return the attachment badge for a filename.
def _file_type_badge(filename: str):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    label, color = _FILE_TYPE_STYLES.get(ext, ((ext.upper()[:4] or "FILE"), "#5F6368"))
    return label, color


# Create a safe attachment filename.
def _safe_download_filename(name: str, fallback: str) -> str:
    name = name or fallback
    cleaned = re.sub(r'[\\/*?:"<>|\r\n]', "_", name)
    cleaned = cleaned.encode("ascii", errors="ignore").decode("ascii").strip(" ._")
    return cleaned or fallback


# Render the selected email or empty reader state.
def render_reader(message):
    st.markdown(
        '<div class="section-label reader-section-label">Email Content</div>',
        unsafe_allow_html=True,
    )

    with st.container(
        height=READER_HEIGHT,
        border=False,
        key="reader_content_scroll",
    ):
        if not message:
            st.markdown(
                '<div class="empty-state">Select an email from the list to view it here.</div>',
                unsafe_allow_html=True,
            )
            return

        email_data = message["email"]
        attachments = message.get("attachments") or []
        sender = email_data.get("from", "")
        subject = email_data.get("subject") or "(No Subject)"
        date_display = email_data.get("date_display", "Unknown")
        initial, avatar_color = _sender_avatar(sender)
        st.markdown(
            f'<div class="reader-header">'
            f'<div class="reader-subject">{html_lib.escape(subject)}</div>'
            f'<div class="reader-meta-row">'
            f'<div class="reader-avatar" style="background:{avatar_color};">{html_lib.escape(initial)}</div>'
            f'<div class="reader-meta">From {html_lib.escape(sender)} &middot; '
            f'{html_lib.escape(date_display)}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _render_message(email_data, attachments)


# Render the email body and attachments.
def _render_message(email_data, attachments=None):
    if email_data.get("body_html"):
        html_content = (
            "<style>"
            ".email-body, .email-body * { max-width: 100% !important; box-sizing: border-box; }"
            ".email-body table { width: 100% !important; }"
            ".email-body img { height: auto !important; }"
            "</style>"
            f'<div class="email-body" style="font-family: -apple-system, BlinkMacSystemFont, '
            f"'Segoe UI', Arial, sans-serif; color: {COLORS['text_primary']}; "
            f"background: {COLORS['bg_card']}; padding: 18px 20px; border-radius: 4px; "
            f'line-height: 1.5; font-size: 14px; overflow-x: auto;">'
            f'{email_data["body_html"]}'
            "</div>"
        )

        st.markdown(html_content, unsafe_allow_html=True)
    else:
        body_text = email_data.get("body_text") or "(No text content)"
        st.markdown(
            f'<div class="reader-body">{html_lib.escape(body_text)}</div>',
            unsafe_allow_html=True,
        )

    if attachments:
        st.markdown(
            f'<div class="section-label" style="margin-top: 1rem;">'
            f'Attachments ({len(attachments)})</div>',
            unsafe_allow_html=True,
        )

        cards_html = []
        for i, a in enumerate(attachments):
            filename = a.get("filename") or f"attachment_{i + 1}"
            data = a.get("data") or b""
            mime = a.get("content_type") or "application/octet-stream"
            label, color = _file_type_badge(filename)
            safe_name = _safe_download_filename(filename, fallback=f"attachment_{i + 1}")
            b64 = base64.b64encode(data).decode("ascii")
            safe_filename_html = html_lib.escape(filename)

            cards_html.append(
                f'<a class="attach-card" download="{html_lib.escape(safe_name)}" '
                f'href="data:{html_lib.escape(mime)};base64,{b64}" title="{safe_filename_html}">'
                f'<div class="attach-thumb">'
                f'<span class="attach-corner" style="border-bottom-color:{color};"></span>'
                f'<span class="attach-badge" style="background:{color};">{label}</span>'
                f'</div>'
                f'<div class="attach-name">{safe_filename_html}</div>'
                f'</a>'
            )

        st.markdown(f'<div class="attach-grid">{"".join(cards_html)}</div>', unsafe_allow_html=True)
