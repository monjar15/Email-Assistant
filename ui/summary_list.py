"""Filterable AI Summary list UI."""
import streamlit as st

from ui.styles import section_label


def _matches_search(item: dict, query: str) -> bool:
    text = " ".join([
        item.get("subject", ""), item.get("from", ""),
        item.get("summary", ""), item.get("priority", ""),
    ]).casefold()
    return not query or query.casefold() in text


def _filter_summaries(summaries: list[dict], filter_key: str, query: str):
    filtered = [item for item in summaries if _matches_search(item, query)]
    if filter_key == "unread":
        return [item for item in filtered if not item.get("is_read", False)]
    if filter_key == "high":
        return [
            item for item in filtered
            if item.get("priority", "").casefold() == "high"
        ]
    return filtered


def _reset_filter_when_search_clears():
    """Restore the full list immediately after clearing the search field."""
    if not st.session_state.get("summary_search_query", "").strip():
        st.session_state.summary_filter = "all"


def render_summary_list(summaries: list[dict]):
    """Render filters and cards; return a newly opened summary ID."""
    st.markdown(section_label("AI Summaries"), unsafe_allow_html=True)
    query = st.text_input(
        "Search summaries", key="summary_search_query",
        placeholder="⌕ Search summaries", label_visibility="collapsed",
        on_change=_reset_filter_when_search_clears,
    ).strip()
    filter_key = st.session_state.get("summary_filter", "all")
    visible_summaries = _filter_summaries(summaries, filter_key, query)

    if not visible_summaries:
        message = "No saved summaries match this filter." if summaries else (
            "Generate a summary from selected Inbox emails to see it here."
        )
        st.markdown(f'<div class="empty-state">{message}</div>', unsafe_allow_html=True)
        return None

    with st.container(height=700, border=False, key="summary_list_scroll"):
        for item in visible_summaries:
            uid = str(item["uid"])
            selected = st.session_state.get("selected_summary_uid") == uid
            priority = item.get("priority", "Medium")
            subject = item.get("subject", "(No Subject)")
            sender = item.get("from", "")
            if st.button(
                f"{priority} · {subject}  \n{sender}", key=f"summary_{uid}",
                use_container_width=True,
                type="primary" if selected else "secondary",
            ):
                return uid
    return None
