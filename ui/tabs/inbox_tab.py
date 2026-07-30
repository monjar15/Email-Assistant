"""The original Inbox workspace, now hosted inside a tab."""
import streamlit as st
from controllers.reader_controller import load_selected_message
from ui.inbox import render_inbox
from ui.reader import render_reader


def render_inbox_tab(activity_slot, folder: str = "INBOX"):
    with st.container(height=700, border=False, key="mail_workspace"):
        col_list, col_content = st.columns([0.4, 0.6], gap="large")
        list_source = st.session_state.search_results if st.session_state.search_active else st.session_state.emails
        if st.session_state.get("inbox_filter") == "unread":
            unread_uids = st.session_state.get("new_email_uids", set())
            list_source = [
                item for item in list_source
                if str(item.get("uid")) in unread_uids
            ]
        with col_list:
            actions = render_inbox(list_source, total=st.session_state.inbox_total,
                                   offset=st.session_state.inbox_offset, loading=st.session_state.loading,
                                   checked_uids=st.session_state.checked_uids,
                                   search_active=st.session_state.search_active,
                                   search_total=st.session_state.search_total,
                                   can_prev=st.session_state.inbox_offset > 0,
                                   can_next=st.session_state.inbox_has_more)
            st.session_state.checked_uids = actions["checked_uids"]
        with col_content:
            render_reader(load_selected_message(list_source, activity_slot, folder=folder))
    return actions, list_source
