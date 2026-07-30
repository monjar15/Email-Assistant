"""Stateful tab navigation without radio-style controls."""
import streamlit as st


INBOX_TAB = "inbox"
SUMMARY_TAB = "summary"


def render_workspace_tabs() -> str:
    """Render icon tabs and return the current workspace identifier."""
    active = st.session_state.get("active_workspace", INBOX_TAB)
    inbox_col, summary_col, _ = st.columns([0.16, 0.20, 0.64], gap="small")
    with inbox_col:
        if st.button(
            "📥 Inbox", key="workspace_tab_inbox", use_container_width=True,
            type="primary" if active == INBOX_TAB else "secondary",
        ):
            st.session_state.active_workspace = INBOX_TAB
            st.rerun()
    with summary_col:
        if st.button(
            "✨ AI Summary", key="workspace_tab_summary", use_container_width=True,
            type="primary" if active == SUMMARY_TAB else "secondary",
        ):
            st.session_state.active_workspace = SUMMARY_TAB
            st.rerun()
    return active
