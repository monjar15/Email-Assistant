import streamlit as st

from ui.styles import section_label

LIST_HEIGHT = 700


# Update search actions when the query changes.
def _handle_search_input_change():
    query = st.session_state.get("inbox_search_query", "").strip()
    st.session_state.inbox_search_submit = bool(query)
    st.session_state.inbox_search_clear = not bool(query)


# Clear the search box and restore the inbox.
def _clear_search_input():
    st.session_state.inbox_search_query = ""
    st.session_state.inbox_search_clear = True
    st.session_state.inbox_search_submit = False


# Render the inbox toolbar and email list.
def render_inbox(emails, total: int = 0, offset: int = 0,
                  loading: bool = False, checked_uids=None,
                  search_active: bool = False, search_total: int = 0,
                  can_prev: bool = None, can_next: bool = None) -> dict:
    if checked_uids is None:
        checked_uids = set()

    with st.container(key="inbox_toolbar"):
        st.markdown(section_label("Inbox"), unsafe_allow_html=True)

        # Keep toolbar buttons visible in narrow inbox panels.
        col_query, col_clear_btn, col_search_btn = st.columns(
            [0.80, 0.09, 0.11], gap="small"
        )
        with col_query:
            query = st.text_input(
                "Search",
                key="inbox_search_query",
                placeholder="Search mail",
                label_visibility="collapsed",
                disabled=loading,
                on_change=_handle_search_input_change,
            )
        with col_clear_btn:
            if query.strip():
                st.button(
                    "✕",
                    key="inbox_clear_search_icon",
                    use_container_width=True,
                    disabled=loading,
                    on_click=_clear_search_input,
                )
        with col_search_btn:
            search_clicked = st.button(
                "🔍",
                key="inbox_search_btn",
                use_container_width=True,
                disabled=loading,
            )

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
            st.markdown(
                f'<div class="item-meta inbox-range-label">{label}</div>',
                unsafe_allow_html=True,
            )
        else:
            start = offset + 1 if total > 0 and emails else 0
            end = offset + len(emails)
            prev_allowed = can_prev if can_prev is not None else offset > 0
            next_allowed = (
                can_next if can_next is not None else offset + len(emails) < total
            )

            col_range, col_refresh, col_prev, col_next = st.columns(
                [0.64, 0.12, 0.12, 0.12], gap="small"
            )
            with col_range:
                st.markdown(
                    f'<div class="item-meta inbox-range-label">'
                    f'{start}–{end} of {total:,}</div>',
                    unsafe_allow_html=True,
                )
            with col_refresh:
                refresh_clicked = st.button(
                    "🔄",
                    key="refresh_inbox_icon",
                    help="Refresh inbox",
                    use_container_width=True,
                    disabled=loading,
                )
            with col_prev:
                prev_clicked = st.button(
                    "‹",
                    key="inbox_prev_page",
                    help="Previous page",
                    use_container_width=True,
                    disabled=(loading or not prev_allowed),
                )
            with col_next:
                next_clicked = st.button(
                    "›",
                    key="inbox_next_page",
                    help="Next page",
                    use_container_width=True,
                    disabled=(loading or not next_allowed),
                )

    actions = {
        "refresh": refresh_clicked,
        "prev": prev_clicked,
        "next": next_clicked,
        "search": search_clicked or submitted_by_input,
        "clear_search": cleared_by_input,
        "query": query,
        "checked_uids": set(checked_uids),
    }

    if not emails:
        empty_msg = (
            "No emails match that search."
            if search_active
            else "No emails are available in the local inbox yet."
        )
        st.markdown(
            f'<div class="empty-state">{empty_msg}</div>', unsafe_allow_html=True
        )
        return actions

    new_checked = set()
    with st.container(height=LIST_HEIGHT, border=False, key="inbox_list_scroll"):
        for email_item in emails:
            uid = str(email_item.get("uid", ""))
            is_selected = st.session_state.get("selected_uid") == uid

            col_check, col_row = st.columns([0.045, 0.955], gap="small")
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

            with col_row:
                subject = email_item.get("subject") or "(No Subject)"
                from_label = email_item.get("from", "")
                clicked = st.button(
                    f"{subject}  \n{from_label}",
                    key=f"email_{uid}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                    disabled=loading,
                )
                if clicked:
                    st.session_state.selected_uid = uid
                    st.rerun()

        # Keep the final card above the scroll container edge.
        st.markdown(
            '<div class="inbox-list-bottom-spacer" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )

    actions["checked_uids"] = new_checked
    return actions
