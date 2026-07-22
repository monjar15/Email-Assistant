import base64
import html as html_lib
import re

import streamlit as st
import streamlit.components.v1 as components

from ui.styles import section_label

# Palette Gmail-style contact avatars cycle through — picked deterministically
# from the sender string so the same person always gets the same color.
_AVATAR_COLORS = ["#C9A24B", "#1A73E8", "#188038", "#E37400", "#9334E6", "#D93025", "#12B5CB", "#7CB342"]


def _sender_avatar(sender: str):
    name = (sender or "?").split("<", 1)[0].strip().strip('"')
    initial = (name[:1] or (sender[:1] if sender else "?")).upper()
    color = _AVATAR_COLORS[sum(ord(ch) for ch in (sender or "")) % len(_AVATAR_COLORS)]
    return initial, color


# (file extension) -> (badge label, badge color) — same color language Gmail
# uses for its attachment thumbnails, so a PDF/spreadsheet/doc reads as
# what it is at a glance instead of every attachment looking identical.
_FILE_TYPE_STYLES = {
    "pdf": ("PDF", "#EA4335"),
    "doc": ("DOC", "#1A73E8"), "docx": ("DOC", "#1A73E8"),
    "xls": ("XLS", "#188038"), "xlsx": ("XLS", "#188038"), "csv": ("CSV", "#188038"),
    "ppt": ("PPT", "#E37400"), "pptx": ("PPT", "#E37400"),
    "zip": ("ZIP", "#5F6368"), "rar": ("RAR", "#5F6368"), "7z": ("7Z", "#5F6368"),
    "png": ("IMG", "#9334E6"), "jpg": ("IMG", "#9334E6"), "jpeg": ("IMG", "#9334E6"), "gif": ("IMG", "#9334E6"),
    "txt": ("TXT", "#5F6368"),
}


def _file_type_badge(filename: str):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    label, color = _FILE_TYPE_STYLES.get(ext, ((ext.upper()[:4] or "FILE"), "#5F6368"))
    return label, color


def _safe_download_filename(name: str, fallback: str) -> str:
    name = name or fallback
    cleaned = re.sub(r'[\\/*?:"<>|\r\n]', "_", name)
    cleaned = cleaned.encode("ascii", errors="ignore").decode("ascii").strip(" ._")
    return cleaned or fallback


def render_reader(thread):
    st.markdown(section_label("Email Content"), unsafe_allow_html=True)

    if not thread:
        st.markdown(
            '<div class="empty-state">Select an email from the list to view it here.</div>',
            unsafe_allow_html=True,
        )
        return

    latest = thread[0]["email"]
    count = len(thread)
    badge_html = (
        f'<span style="margin-left:8px; padding:2px 8px; border-radius:10px; '
        f'background:#3a3a3a; color:#bdbdbd; font-size:0.75rem; vertical-align:middle;">'
        f'{count} messages</span>'
        if count > 1 else ""
    )

    # Subject and the newest message's from/date row share one wrapper,
    # same as the original single-message layout — splitting them into
    # separate blocks drops the styling context and misaligns the row.
    initial, avatar_color = _sender_avatar(latest["from"])
    st.markdown(
        f'<div class="reader-header">'
        f'<div class="reader-subject">{latest["subject"]}{badge_html}</div>'
        f'<div class="reader-meta-row">'
        f'<div class="reader-avatar" style="background:{avatar_color};">{initial}</div>'
        f'<div class="reader-meta">From {latest["from"]} &middot; {latest["date_display"]}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    _render_message(latest, thread[0]["attachments"])

    if count > 1:
        # Every older message collapsed into a one-line summary — click
        # to expand, same as Gmail's conversation view.
        for msg in thread[1:]:
            email_data = msg["email"]
            attachments = msg["attachments"]
            summary = f'{email_data["from"]}  \u00b7  {email_data["date_display"]}'
            with st.expander(summary, expanded=False):
                _render_message(email_data, attachments)


def _render_message(email_data, attachments=None):
    if email_data.get("body_html"):
        components.html(
            f"""
            <style>
                html, body {{ margin: 0; padding: 0; }}
                /* Marketing templates often hardcode a fixed pixel width
                   (a 600-700px table is standard for email), which is
                   what made some messages look oversized/cut off in this
                   narrower panel. Capping width/max-width on the common
                   structural tags forces them back down to the
                   container instead of overflowing it. */
                .email-body, .email-body * {{
                    max-width: 100% !important;
                    box-sizing: border-box;
                }}
                .email-body table {{
                    width: 100% !important;
                }}
                .email-body img {{
                    height: auto !important;
                }}
            </style>
            <div class="email-body" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        color: #1a1a1a; background: #ffffff; padding: 18px 20px;
                        border-radius: 4px; line-height: 1.5; font-size: 14px;
                        overflow-x: auto;">
                {email_data['body_html']}
            </div>
            """,
            height=560,
            scrolling=True,
        )
    else:
        st.markdown(
            f'<div class="reader-body">{email_data["body_text"] or "(No text content)"}</div>',
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
                f'href="data:{mime};base64,{b64}" title="{safe_filename_html}">'
                f'<div class="attach-thumb">'
                f'<span class="attach-corner" style="border-bottom-color:{color};"></span>'
                f'<span class="attach-badge" style="background:{color};">{label}</span>'
                f'</div>'
                f'<div class="attach-name">{safe_filename_html}</div>'
                f'</a>'
            )

        st.markdown(f'<div class="attach-grid">{"".join(cards_html)}</div>', unsafe_allow_html=True)
