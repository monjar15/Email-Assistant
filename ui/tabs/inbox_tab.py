"""The original Inbox workspace, now hosted inside a tab."""
import streamlit as st
from controllers.reader_controller import load_selected_message
from ui.inbox import render_inbox
from ui.reader import render_reader


def _sort_value(email_item: dict, arrange_by: str, unread_uids: set[str]):
    uid = str(email_item.get("uid", ""))
    if arrange_by == "date":
        # ISO dates sort chronologically as strings; UID keeps equal/blank values stable.
        return (str(email_item.get("date") or ""), uid.zfill(24))
    if arrange_by == "from":
        return str(email_item.get("from") or "").casefold()
    if arrange_by == "to":
        return str(email_item.get("to") or "").casefold()
    if arrange_by == "status":
        return "unread" if uid in unread_uids else "read"
    if arrange_by == "subject":
        return str(email_item.get("subject") or "").casefold()
    if arrange_by == "attachment":
        value = email_item.get("has_attachment")
        if value is None:
            value = bool(email_item.get("attachments"))
        return (1 if value else 0, str(email_item.get("subject") or "").casefold())
    if arrange_by == "importance":
        value = (
            email_item.get("importance")
            or email_item.get("priority")
            or email_item.get("x_priority")
            or "normal"
        )
        return str(value).casefold()
    return str(email_item.get("subject") or "").casefold()


def _apply_inbox_view_options(emails: list[dict]) -> list[dict]:
    visible = list(emails)
    unread_uids = {str(uid) for uid in st.session_state.get("new_email_uids", set())}

    if st.session_state.get("inbox_filter") == "unread":
        visible = [
            item for item in visible
            if str(item.get("uid", "")) in unread_uids
        ]

    arrange_by = st.session_state.get("inbox_arrange_by")
    sort_order = st.session_state.get("inbox_sort_order")

    # Arrange and Sort are optional. If only one is selected, use a sensible
    # implicit companion without visually selecting another menu option.
    if arrange_by or sort_order:
        effective_arrange = arrange_by or "subject"
        effective_order = sort_order or ("desc" if effective_arrange == "date" else "asc")
        visible.sort(
            key=lambda item: _sort_value(item, effective_arrange, unread_uids),
            reverse=effective_order == "desc",
        )
    return visible


def render_inbox_tab(activity_slot, folder: str = "INBOX"):
    with st.container(border=False, key="mail_workspace"):
        col_list, col_content = st.columns([0.4, 0.6], gap="large")
        source = (
            st.session_state.search_results
            if st.session_state.search_active
            else st.session_state.emails
        )
        list_source = _apply_inbox_view_options(source)

        with col_list:
            with st.container(key="inbox_outer_pane"):
                st.markdown('<div class="pane-heading">Inbox</div>', unsafe_allow_html=True)
                actions = render_inbox(
                    list_source,
                    total=st.session_state.inbox_total,
                    offset=st.session_state.inbox_offset,
                    loading=st.session_state.loading,
                    checked_uids=st.session_state.checked_uids,
                    search_active=st.session_state.search_active,
                    search_total=st.session_state.search_total,
                    can_prev=st.session_state.inbox_offset > 0,
                    can_next=st.session_state.inbox_has_more,
                )
                st.session_state.checked_uids = actions["checked_uids"]
        with col_content:
            with st.container(key="email_content_outer_pane"):
                st.markdown(
                    '<div class="pane-heading pane-heading-right">Email Content</div>',
                    unsafe_allow_html=True,
                )
                render_reader(load_selected_message(list_source, activity_slot, folder=folder))
    return actions, list_source
