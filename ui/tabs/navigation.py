"""Sidebar navigation for the MailMind AI workspaces."""
import streamlit as st

from ui.summary_metrics import todo_task_count

INBOX_TAB = "inbox"
SUMMARY_TAB = "summary"
TODO_TAB = "todo"


def _render_nav_item(key: str, icon: str, label: str, active: bool, count=None, submeta_html: str | None = None) -> bool:
    with st.container(key=f"sidebar_nav_row_{key}"):
        clicked = st.button(
            f"{icon}  {label}",
            key=f"sidebar_nav_{key}",
            use_container_width=True,
            type="primary" if active else "secondary",
        )
        if count is not None:
            st.markdown(
                f'<span class="sidebar-nav-count">{int(count):,}</span>',
                unsafe_allow_html=True,
            )
        if submeta_html:
            st.markdown(submeta_html, unsafe_allow_html=True)
        return clicked


def render_sidebar_navigation() -> str:
    """Render the main workspace navigation inside the sidebar."""
    active = st.session_state.get("active_workspace", INBOX_TAB)
    emails = st.session_state.get("emails", [])
    unread_uids = st.session_state.get("new_email_uids", set())
    inbox_count = st.session_state.get("inbox_total", len(emails))
    summaries = st.session_state.get("summaries", [])
    summary_count = len(summaries)
    task_count = todo_task_count(summaries)
    unread_count = sum(str(item.get("uid")) in unread_uids for item in emails)

    items = [
        (
            INBOX_TAB,
            "✉",
            "Inbox",
            inbox_count,
            (
                '<div class="sidebar-nav-submeta-wrap">'
                f'<span class="sidebar-nav-submeta">{unread_count:,} unread</span>'
                '<span class="sidebar-nav-subdot" aria-hidden="true"></span>'
                '</div>'
            ),
        ),
        (SUMMARY_TAB, "✨", "AI Summary", summary_count, None),
        (TODO_TAB, "☑", "Todo List", task_count, None),
    ]

    for key, icon, label, count, submeta_html in items:
        if _render_nav_item(key, icon, label, active == key, count, submeta_html=submeta_html):
            st.session_state.active_workspace = key
            st.rerun()

    return st.session_state.get("active_workspace", active)
