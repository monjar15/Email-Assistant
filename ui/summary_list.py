"""Filterable and paginated AI Summary list with an Inbox-style UI."""
import html as html_lib

import streamlit as st

from ui.inbox import _display_sender, _inbox_time_label, _sender_avatar
from ui.summary_metrics import deadline_matches, is_task_ready

SUMMARY_LIST_HEIGHT = 820
SUMMARY_PAGE_SIZE = 50


def _matches_search(item: dict, query: str) -> bool:
    text = " ".join([
        item.get("subject", ""),
        item.get("from", ""),
        item.get("summary", ""),
        item.get("priority", ""),
        item.get("status", ""),
    ]).casefold()
    return not query or query.casefold() in text




def _status_label_and_class(status: str) -> tuple[str, str]:
    key = str(status or "Pending").strip().casefold().replace("_", " ")
    if key in {"complete", "completed", "done"}:
        return "COMPLETE", "status-complete"
    if key in {"in progress", "in-progress", "ongoing"}:
        return "IN PROGRESS", "status-in-progress"
    return "PENDING", "status-pending"

def _priority_rank(priority: str) -> int:
    ranks = {"high": 0, "medium": 1, "low": 2}
    return ranks.get(str(priority or "medium").casefold(), 3)


def _sort_value(item: dict, arrange_by: str):
    if arrange_by == "date":
        return (str(item.get("date") or ""), str(item.get("uid", "")).zfill(24))
    if arrange_by == "priority":
        return (
            _priority_rank(item.get("priority", "Medium")),
            str(item.get("subject") or "").casefold(),
        )
    if arrange_by == "from":
        return str(item.get("from") or "").casefold()
    return str(item.get("subject") or "").casefold()


def _handle_summary_search_change():
    st.session_state.summary_offset = 0
    if not st.session_state.get("summary_search_query", "").strip():
        st.session_state.summary_filter = "all"


def _set_summary_menu_value(state_key: str, value: str):
    current_value = st.session_state.get(state_key)
    st.session_state[state_key] = None if current_value == value else value
    st.session_state.summary_offset = 0
    st.session_state.selected_summary_uid = None
    st.session_state.summary_filter_popover_version = (
        st.session_state.get("summary_filter_popover_version", 0) + 1
    )


def _menu_button(label: str, key: str, state_key: str, value: str):
    active = st.session_state.get(state_key) == value
    st.button(
        label,
        key=key,
        type="primary" if active else "secondary",
        use_container_width=True,
        on_click=_set_summary_menu_value,
        args=(state_key, value),
    )


def _render_summary_filter_menu():
    with st.container(key="summary_filter_popover"):
        popover_version = st.session_state.get("summary_filter_popover_version", 0)
        popover_label = "Filters" + ("\u2060" if popover_version % 2 else "")
        with st.popover(
            popover_label,
            icon=":material/filter_alt:",
            use_container_width=True,
        ):
            st.markdown(
                '<div class="inbox-filter-menu-title">FILTER</div>'
                '<div class="inbox-filter-menu-spacer"></div>',
                unsafe_allow_html=True,
            )
            _menu_button(
                "All Summaries", "summary_filter_item_all", "summary_filter", "all"
            )
            _menu_button(
                "Unread", "summary_filter_item_unread", "summary_filter", "unread"
            )
            _menu_button(
                "High Priority", "summary_filter_item_high", "summary_filter", "high"
            )

            st.markdown(
                '<div class="inbox-filter-menu-divider"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="inbox-filter-menu-title">ARRANGE BY</div>'
                '<div class="inbox-filter-menu-spacer"></div>',
                unsafe_allow_html=True,
            )
            _menu_button(
                "Date", "summary_filter_item_arrange_date", "summary_arrange_by", "date"
            )
            _menu_button(
                "Priority",
                "summary_filter_item_arrange_priority",
                "summary_arrange_by",
                "priority",
            )
            _menu_button(
                "From", "summary_filter_item_arrange_from", "summary_arrange_by", "from"
            )
            _menu_button(
                "Subject",
                "summary_filter_item_arrange_subject",
                "summary_arrange_by",
                "subject",
            )

            st.markdown(
                '<div class="inbox-filter-menu-divider"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="inbox-filter-menu-title">SORT</div>'
                '<div class="inbox-filter-menu-spacer"></div>',
                unsafe_allow_html=True,
            )
            _menu_button(
                "A to Z", "summary_filter_item_sort_asc", "summary_sort_order", "asc"
            )
            _menu_button(
                "Z to A", "summary_filter_item_sort_desc", "summary_sort_order", "desc"
            )


def _apply_summary_view_options(
    summaries: list[dict], filter_key: str, query: str
) -> list[dict]:
    visible = [item for item in summaries if _matches_search(item, query)]
    if filter_key == "unread":
        visible = [item for item in visible if not item.get("is_read", False)]
    elif filter_key in {"high", "priority_high"}:
        visible = [
            item for item in visible
            if str(item.get("priority", "")).strip().casefold() == "high"
        ]
    elif filter_key == "priority_medium":
        visible = [
            item for item in visible
            if str(item.get("priority", "Medium")).strip().casefold() == "medium"
        ]
    elif filter_key == "priority_low":
        visible = [
            item for item in visible
            if str(item.get("priority", "")).strip().casefold() == "low"
        ]
    elif filter_key.startswith("status_"):
        wanted = filter_key.removeprefix("status_")
        def normalized_status(item):
            key = str(item.get("status", "Pending")).strip().casefold().replace("_", " ")
            if key in {"complete", "completed", "done"}:
                return "complete"
            if key in {"in progress", "in-progress", "ongoing"}:
                return "in_progress"
            return "pending"
        visible = [
            item for item in visible
            if is_task_ready(item) and normalized_status(item) == wanted
        ]
    elif filter_key.startswith("deadline_"):
        wanted = filter_key.removeprefix("deadline_")
        visible = [item for item in visible if deadline_matches(item, wanted)]

    arrange_by = st.session_state.get("summary_arrange_by")
    sort_order = st.session_state.get("summary_sort_order")
    if arrange_by or sort_order:
        effective_arrange = arrange_by or "date"
        effective_order = sort_order or (
            "desc" if effective_arrange == "date" else "asc"
        )
        visible.sort(
            key=lambda item: _sort_value(item, effective_arrange),
            reverse=effective_order == "desc",
        )
    return visible


def _reload_summaries():
    store = st.session_state.get("summary_store")
    if store is None:
        return

    refreshed = store.load_all("INBOX")
    st.session_state.summaries = refreshed
    st.session_state.summary_offset = 0

    selected_uid = str(st.session_state.get("selected_summary_uid") or "")
    valid_uids = {str(item.get("uid", "")) for item in refreshed}
    if selected_uid not in valid_uids:
        st.session_state.selected_summary_uid = (
            str(refreshed[0]["uid"]) if refreshed else None
        )


def render_summary_list(summaries: list[dict]):
    """Render toolbar and summary cards; return a newly opened summary ID."""
    with st.container(key="summary_toolbar"):
        col_query, col_filter = st.columns([0.80, 0.20], gap="small")
        with col_query:
            query = st.text_input(
                "Search summaries",
                key="summary_search_query",
                placeholder="Search summaries",
                label_visibility="collapsed",
                on_change=_handle_summary_search_change,
            ).strip()
        with col_filter:
            _render_summary_filter_menu()

        filter_key = st.session_state.get("summary_filter", "all")
        visible_summaries = _apply_summary_view_options(summaries, filter_key, query)
        total_visible = len(visible_summaries)

        page_size = int(st.session_state.get("summary_page_size", SUMMARY_PAGE_SIZE))
        page_size = max(1, page_size)
        offset = max(0, int(st.session_state.get("summary_offset", 0)))
        if total_visible == 0:
            offset = 0
        elif offset >= total_visible:
            offset = ((total_visible - 1) // page_size) * page_size
        st.session_state.summary_offset = offset

        page_items = visible_summaries[offset: offset + page_size]
        start = offset + 1 if page_items else 0
        end = offset + len(page_items)
        can_prev = offset > 0
        can_next = offset + page_size < total_visible

        col_range, col_refresh, col_prev, col_next = st.columns(
            [0.64, 0.12, 0.12, 0.12], gap=None
        )
        with col_range:
            st.markdown(
                f'<div class="item-meta inbox-range-label">'
                f'{start}–{end} of {total_visible:,}</div>',
                unsafe_allow_html=True,
            )
        with col_refresh:
            refresh_clicked = st.button(
                "↻", key="refresh_summary_icon", use_container_width=True
            )
        with col_prev:
            prev_clicked = st.button(
                "‹",
                key="summary_prev_page",
                use_container_width=True,
                disabled=not can_prev,
            )
        with col_next:
            next_clicked = st.button(
                "›",
                key="summary_next_page",
                use_container_width=True,
                disabled=not can_next,
            )

        if refresh_clicked:
            _reload_summaries()
            st.rerun()
        if prev_clicked:
            st.session_state.summary_offset = max(0, offset - page_size)
            st.rerun()
        if next_clicked:
            st.session_state.summary_offset = offset + page_size
            st.rerun()

    if not page_items:
        message = (
            "No saved summaries match the current search or filter."
            if summaries
            else "Generate a summary from selected Inbox emails to see it here."
        )
        with st.container(
            height=SUMMARY_LIST_HEIGHT, border=False, key="summary_list_scroll"
        ):
            st.markdown(
                f'<div class="empty-state inbox-empty-state">{message}</div>',
                unsafe_allow_html=True,
            )
        return None

    with st.container(
        height=SUMMARY_LIST_HEIGHT, border=False, key="summary_list_scroll"
    ):
        for item in page_items:
            uid = str(item.get("uid", ""))
            selected = str(st.session_state.get("selected_summary_uid") or "") == uid
            unread = not item.get("is_read", False)
            priority = str(item.get("priority") or "Medium").strip()
            priority_key = priority.casefold()
            if priority_key not in {"high", "medium", "low"}:
                priority_key = "medium"
            status_label, status_class = _status_label_and_class(
                item.get("status", "Pending")
            )
            has_task_data = bool(item.get("action_items") or item.get("deadlines"))
            sender = item.get("from", "")
            sender_text = _display_sender(sender)
            avatar_initial, avatar_class = _sender_avatar(sender)
            subject = item.get("subject") or "(No Subject)"
            time_label = _inbox_time_label(item)
            selected_class = " is-selected" if selected else ""
            unread_class = " is-summary-unread" if unread else ""

            with st.container(key=f"summary_card_{uid}"):
                st.markdown(
                    f"""
                    <div class="summary-row-shell">
                        <span class="summary-static-checkbox" aria-hidden="true"></span>
                        <div class="mail-row-card summary-mail-row{selected_class}{unread_class}">
                            <div class="mail-row-avatar {avatar_class}">
                                {html_lib.escape(avatar_initial)}
                            </div>
                            <div class="mail-row-copy">
                                <div class="mail-row-subject">{html_lib.escape(subject)}</div>
                                <div class="mail-row-sender">
                                    {html_lib.escape(sender_text)}
                                </div>
                            </div>
                            <div class="mail-row-time">{html_lib.escape(time_label)}</div>
                            <div class="summary-list-badge-stack">
                                {f'<span class="summary-list-status-pill {status_class}">{html_lib.escape(status_label)}</span>' if has_task_data else '<span class="summary-list-status-pill status-placeholder" aria-hidden="true"></span>'}
                                <span class="summary-list-priority-pill priority-{priority_key}">{html_lib.escape(priority.upper())}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                clicked = st.button(
                    "Open summary",
                    key=f"summary_item_{uid}",
                    use_container_width=True,
                )
                if clicked:
                    return uid

            # Use a real Streamlit element for the gap. Margin on the keyed
            # card wrapper can be swallowed by Streamlit's layout wrappers.
            st.markdown(
                '<div class="summary-card-gap" aria-hidden="true"></div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="inbox-list-bottom-spacer" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
    return None
