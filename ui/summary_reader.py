"""Reader UI for one structured AI email summary."""
import html
import streamlit as st
from ui.reader import _sender_avatar


def _section(title: str, values):
    content = values or ["None identified."]
    items = "".join(f"<li>{html.escape(value)}</li>" for value in content)
    st.markdown(f'<div class="summary-section"><strong>{title}</strong><ul>{items}</ul></div>', unsafe_allow_html=True)


def render_summary_reader(summary):
    st.markdown('<div class="section-label reader-section-label">AI Summary</div>', unsafe_allow_html=True)
    with st.container(height=720, border=False, key="summary_reader_scroll"):
        if not summary:
            st.markdown('<div class="empty-state">Select a summarized email to view its AI summary here.</div>', unsafe_allow_html=True)
            return
        sender = summary.get("from", "")
        initial, color = _sender_avatar(sender)
        st.markdown(
            f'<div class="reader-header"><div class="reader-subject">{html.escape(summary.get("subject", "(No Subject)"))}</div>'
            f'<div class="reader-meta-row"><div class="reader-avatar" style="background:{color};">{html.escape(initial)}</div>'
            f'<div class="reader-meta">From {html.escape(sender)} &middot; To {html.escape(summary.get("to", ""))} &middot; {html.escape(summary.get("date_display", "Unknown"))}</div>'
            '</div></div>', unsafe_allow_html=True,
        )
        st.markdown(f'<div class="reader-body summary-overview">{html.escape(summary.get("summary", ""))}</div>', unsafe_allow_html=True)
        _section("Priority", [summary.get("priority", "Medium")])
        _section("Key Points", summary.get("key_points"))
        _section("Important Deadlines", summary.get("deadlines"))
        _section("Action Items", summary.get("action_items"))
