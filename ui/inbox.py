import html as html_lib

import streamlit as st

from datetime import datetime, timedelta
from email.utils import parseaddr

LIST_HEIGHT = 820

_AVATAR_CLASS_COUNT = 8


def _sender_avatar(sender: str):
    name, address = parseaddr(sender or "")
    label = (name or address or sender or "?").strip().strip('"')
    initial = (label[:1] or "?").upper()
    tone_index = sum(ord(ch) for ch in (sender or "")) % _AVATAR_CLASS_COUNT
    return initial, f"avatar-tone-{tone_index}"


def _display_sender(sender: str) -> str:
    name, address = parseaddr(sender or "")
    return (name or address or sender or "Unknown sender").strip()


def _inbox_time_label(email_item: dict) -> str:
    date_value = str(email_item.get("date") or "").strip()
    try:
        dt = datetime.fromisoformat(date_value) if date_value else None
    except Exception:
        dt = None

    if not dt:
        raw = str(email_item.get("date_display") or "").strip()
        return raw or "Unknown"

    try:
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    except Exception:
        now = datetime.now()

    today = now.date()
    item_day = dt.date()
    if item_day == today:
        return dt.strftime("%I:%M %p").lstrip("0")
    if item_day == (today - timedelta(days=1)):
        return "Yesterday"
    if item_day.year == today.year:
        return dt.strftime("%b %d").replace(" 0", " ")
    return dt.strftime("%b %d, %Y").replace(" 0", " ")


# Update search actions when the query changes.
def _handle_search_input_change():
    query = st.session_state.get("inbox_search_query", "").strip()
    st.session_state.inbox_search_submit = bool(query)
    st.session_state.inbox_search_clear = not bool(query)


# Toggle one filter-menu choice. Selecting the active option again clears it.
def _set_filter_menu_value(state_key: str, value: str):
    current_value = st.session_state.get(state_key)
    st.session_state[state_key] = None if current_value == value else value

    # Changing the invisible popover label identity forces the open menu to close
    # after Streamlit reruns, without changing the visible "Filters" text.
    st.session_state.inbox_filter_popover_version = (
        st.session_state.get("inbox_filter_popover_version", 0) + 1
    )

    # A changed filter can make the currently open email disappear.
    st.session_state.selected_uid = None


def _menu_button(label: str, key: str, state_key: str, value: str):
    active = st.session_state.get(state_key) == value
    st.button(
        label,
        key=key,
        type="primary" if active else "secondary",
        use_container_width=True,
        on_click=_set_filter_menu_value,
        args=(state_key, value),
    )


def _render_filter_menu(loading: bool = False):
    # Streamlit 1.50 has no key parameter on st.popover, so a keyed
    # container provides a stable CSS hook for the trigger button.
    with st.container(key="inbox_filter_popover"):
        popover_version = st.session_state.get("inbox_filter_popover_version", 0)
        # WORD JOINER is invisible, but makes the popover a fresh element after a
        # selection. That reliably collapses the open menu on the rerun.
        popover_label = "Filters" + ("\u2060" if popover_version % 2 else "")
        with st.popover(
            popover_label,
            icon=":material/filter_alt:",
            use_container_width=True,
            disabled=loading,
        ):
            st.markdown('<div class="inbox-filter-menu-title">FILTER</div><div class="inbox-filter-menu-spacer"></div>', unsafe_allow_html=True)
            _menu_button(
                "All Mail",
                "inbox_filter_item_all",
                "inbox_filter",
                "all",
            )
            _menu_button(
                "Unread Mail",
                "inbox_filter_item_unread",
                "inbox_filter",
                "unread",
            )

            st.markdown('<div class="inbox-filter-menu-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="inbox-filter-menu-title">ARRANGE BY</div><div class="inbox-filter-menu-spacer"></div>', unsafe_allow_html=True)
            for value, label in [
                ("date", "Date"),
                ("from", "From"),
                ("to", "To"),
                ("status", "Status"),
                ("subject", "Subject"),
                ("attachment", "Attachment"),
                ("importance", "Importance"),
            ]:
                _menu_button(
                    label,
                    f"inbox_filter_item_arrange_{value}",
                    "inbox_arrange_by",
                    value,
                )

            st.markdown('<div class="inbox-filter-menu-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="inbox-filter-menu-title">SORT</div><div class="inbox-filter-menu-spacer"></div>', unsafe_allow_html=True)
            _menu_button(
                "A to Z",
                "inbox_filter_item_sort_asc",
                "inbox_sort_order",
                "asc",
            )
            _menu_button(
                "Z to A",
                "inbox_filter_item_sort_desc",
                "inbox_sort_order",
                "desc",
            )


# Render the inbox toolbar and email list.
def render_inbox(emails, total: int = 0, offset: int = 0,
                  loading: bool = False, checked_uids=None,
                  search_active: bool = False, search_total: int = 0,
                  can_prev: bool = None, can_next: bool = None) -> dict:
    if checked_uids is None:
        checked_uids = set()

    with st.container(key="inbox_toolbar"):
        col_query, col_filter = st.columns([0.78, 0.22], gap="small")
        with col_query:
            query = st.text_input(
                "Search",
                key="inbox_search_query",
                placeholder="Search mail",
                label_visibility="collapsed",
                disabled=loading,
                on_change=_handle_search_input_change,
            )
        with col_filter:
            _render_filter_menu(loading=loading)

        submitted_by_input = st.session_state.pop("inbox_search_submit", False)
        cleared_by_input = st.session_state.pop("inbox_search_clear", False)

        refresh_clicked = False
        prev_clicked = False
        next_clicked = False

        if search_active:
            shown = len(emails)
            label = f"{search_total:,} result{'s' if search_total != 1 else ''}"
            if search_total > shown:
                label += f" · showing first {shown:,}"
            col_range, col_refresh = st.columns([0.86, 0.14], gap="small")
            with col_range:
                st.markdown(
                    f'<div class="item-meta inbox-range-label">{label}</div>',
                    unsafe_allow_html=True,
                )
            with col_refresh:
                refresh_clicked = st.button(
                    "↻",
                    key="refresh_inbox_icon",
                    use_container_width=True,
                    disabled=loading,
                )
        else:
            start = offset + 1 if total > 0 and emails else 0
            end = offset + len(emails)
            prev_allowed = can_prev if can_prev is not None else offset > 0
            next_allowed = (
                can_next if can_next is not None else offset + len(emails) < total
            )

            col_range, col_refresh, col_prev, col_next = st.columns(
                [0.64, 0.12, 0.12, 0.12], gap=None
            )
            with col_range:
                st.markdown(
                    f'<div class="item-meta inbox-range-label">'
                    f'{start}–{end} of {total:,}</div>',
                    unsafe_allow_html=True,
                )
            with col_refresh:
                refresh_clicked = st.button(
                    "↻",
                    key="refresh_inbox_icon",
                    use_container_width=True,
                    disabled=loading,
                )
            with col_prev:
                prev_clicked = st.button(
                    "‹",
                    key="inbox_prev_page",
                    use_container_width=True,
                    disabled=(loading or not prev_allowed),
                )
            with col_next:
                next_clicked = st.button(
                    "›",
                    key="inbox_next_page",
                    use_container_width=True,
                    disabled=(loading or not next_allowed),
                )

    actions = {
        "refresh": refresh_clicked,
        "prev": prev_clicked,
        "next": next_clicked,
        "search": submitted_by_input,
        "clear_search": cleared_by_input,
        "query": query,
        "checked_uids": set(checked_uids),
    }

    if not emails:
        empty_msg = (
            "No emails match the current search or filter."
            if search_active or st.session_state.get("inbox_filter") == "unread"
            else "No emails are available in the local inbox yet."
        )
        with st.container(height=LIST_HEIGHT, border=False, key="inbox_list_scroll"):
            st.markdown(
                f'<div class="empty-state inbox-empty-state">{empty_msg}</div>',
                unsafe_allow_html=True,
            )
        return actions

    visible_uids = {str(email_item.get("uid", "")) for email_item in emails}
    # Preserve choices from other inbox pages while the current page changes.
    new_checked = set(checked_uids) - visible_uids
    with st.container(height=LIST_HEIGHT, border=False, key="inbox_list_scroll"):
        for email_item in emails:
            uid = str(email_item.get("uid", ""))
            is_selected = st.session_state.get("selected_uid") == uid
            is_new = uid in st.session_state.get("new_email_uids", set())

            col_check, col_row = st.columns([0.038, 0.962], gap="small")
            with col_check:
                checked = st.checkbox(
                    "Select",
                    key=f"chk_{uid}",
                    value=uid in checked_uids,
                    disabled=loading,
                    label_visibility="collapsed",
                )
                if checked:
                    new_checked.add(uid)

            sender_text = _display_sender(email_item.get("from", ""))
            avatar_initial, avatar_class = _sender_avatar(email_item.get("from", ""))
            subject = email_item.get("subject") or "(No Subject)"
            time_label = _inbox_time_label(email_item)
            selected_class = " is-selected" if is_selected else ""
            new_class = " is-new" if is_new else ""

            with col_row:
                with st.container(key=f"inbox_card_{uid}"):
                    st.markdown(
                        f"""
                        <div class="mail-row-card{selected_class}{new_class}">
                            <div class="mail-row-avatar {avatar_class}">
                                {html_lib.escape(avatar_initial)}
                            </div>
                            <div class="mail-row-copy">
                                <div class="mail-row-subject">{html_lib.escape(subject)}</div>
                                <div class="mail-row-sender">{html_lib.escape(sender_text)}</div>
                            </div>
                            <div class="mail-row-time">{html_lib.escape(time_label)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    clicked = st.button(
                        "Open email",
                        key=f"email_{uid}",
                        use_container_width=True,
                        disabled=loading,
                    )
                    if clicked:
                        st.session_state.selected_uid = uid
                        st.session_state.new_email_uids.discard(uid)
                        st.rerun()

        # Keep the final card above the scroll container edge.
        st.markdown(
            '<div class="inbox-list-bottom-spacer" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )

    actions["checked_uids"] = new_checked
    return actions
