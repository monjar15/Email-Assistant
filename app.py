import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from controllers.inbox_controller import (
    check_new_messages,
    handle_inbox_actions,
    load_inbox_if_needed,
    render_new_mail_notice,
    run_full_sync_if_needed,
)
from controllers.reader_controller import load_selected_message
from controllers.session_controller import (
    bind_store_to_signed_in_account,
    initialize_session_state,
    restore_saved_session,
)
from ui.inbox import render_inbox
from ui.reader import render_reader
from ui.sidebar import render_login_form, render_logout_button, render_status
from ui.styles import brand_header, get_css

st.set_page_config(
    page_title="MailMind AI — Email Assistant",
    page_icon="✒",
    layout="wide",
)
st.markdown(get_css(), unsafe_allow_html=True)

initialize_session_state()

NEW_MAIL_CHECK_SECONDS = 30
WORKSPACE_HEIGHT = 700
FOLDER = "INBOX"

# Restore a live server-side login after a browser refresh.
restore_saved_session()

with st.container(key="app_brand_header"):
    st.markdown(
        brand_header("MailMind AI", "AI-Assisted Inbox &amp; Task Management"),
        unsafe_allow_html=True,
    )

info_slot = st.empty()
login_slot = st.sidebar.empty()
status_slot = st.sidebar.empty()
activity_slot = st.sidebar.empty()

if not st.session_state.logged_in:
    with info_slot.container():
        st.info("Log in with your email account from the sidebar to get started.")
    with login_slot.container():
        render_login_form()
    st.stop()

bind_store_to_signed_in_account()

with status_slot.container():
    render_logout_button()
    render_status()

# Load the saved inbox and complete the first mailbox sync when needed.
load_inbox_if_needed(activity_slot, folder=FOLDER)
run_full_sync_if_needed(activity_slot, folder=FOLDER)

# Check the remote message count without downloading the mailbox.
check_new_messages(
    folder=FOLDER,
    check_seconds=NEW_MAIL_CHECK_SECONDS,
)
render_new_mail_notice()

with st.container(height=WORKSPACE_HEIGHT, border=False, key="mail_workspace"):
    col_list, col_content = st.columns([0.4, 0.6], gap="large")

    with col_list:
        list_source = (
            st.session_state.search_results
            if st.session_state.search_active
            else st.session_state.emails
        )
        inbox_actions = render_inbox(
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
        st.session_state.checked_uids = inbox_actions["checked_uids"]

    with col_content:
        selected_message = load_selected_message(
            list_source,
            activity_slot,
            folder=FOLDER,
        )
        render_reader(selected_message)

# Process search, refresh, and pagination after the interface is rendered.
handle_inbox_actions(
    inbox_actions,
    activity_slot,
    folder=FOLDER,
)
