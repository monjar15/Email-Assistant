import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from controllers.inbox_controller import (
    check_new_messages,
    handle_inbox_actions,
    has_checked_emails,
    load_inbox_if_needed,
    render_new_mail_notice,
    run_full_sync_if_needed,
)
from controllers.summary_controller import (
    monitor_summary_generation,
    start_summary_generation,
)
from services.ai_service import get_ollama_status
from controllers.session_controller import (
    bind_store_to_signed_in_account,
    initialize_session_state,
    restore_saved_session,
)
from ui.sidebar import (
    render_login_form,
    render_inbox_filters,
    render_logout_button,
    render_ollama_prompt,
    render_summary_filters,
    render_status,
    render_summary_button,
)
from ui.styles import brand_header, get_css
from ui.tabs.inbox_tab import render_inbox_tab
from ui.tabs.navigation import INBOX_TAB, SUMMARY_TAB, render_workspace_tabs
from ui.tabs.summary_tab import render_summary_tab

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
summary_action_slot = st.sidebar.empty()
summary_filter_slot = st.sidebar.empty()
activity_slot = st.sidebar.empty()

if not st.session_state.logged_in:
    with info_slot.container():
        st.info("Log in with your email account from the sidebar to get started.")
    with login_slot.container():
        render_login_form()
    st.stop()

bind_store_to_signed_in_account()

# Load the saved inbox and complete the first mailbox sync when needed.
load_inbox_if_needed(activity_slot, folder=FOLDER)
run_full_sync_if_needed(activity_slot, folder=FOLDER)

# Check the remote message count without downloading the mailbox.
check_new_messages(
    folder=FOLDER,
    check_seconds=NEW_MAIL_CHECK_SECONDS,
)
render_new_mail_notice()
email_deletion_notice = st.session_state.pop("email_deletion_notice", "")
if email_deletion_notice:
    st.info(email_deletion_notice)

# A lightweight Streamlit fragment refreshes the activity bar once per second.
# The summary worker itself remains independent, so navigation cannot stop it.
monitor_summary_generation(activity_slot, folder=FOLDER)

pending_clear = (
    st.session_state.pop("clear_checked_after_summary", [])
    + st.session_state.pop("clear_checked_after_refresh", [])
)
if pending_clear:
    st.session_state.checked_uids = set()
    for uid in pending_clear:
        st.session_state[f"chk_{uid}"] = False

if st.session_state.pop("switch_to_summary", False):
    st.session_state.active_workspace = SUMMARY_TAB
if st.session_state.active_workspace not in {INBOX_TAB, SUMMARY_TAB}:
    st.session_state.active_workspace = INBOX_TAB
active_workspace = render_workspace_tabs()

with st.sidebar:
    with st.container(key="sidebar_footer"):
        render_status()
        render_logout_button()

generate_clicked = False
if active_workspace == INBOX_TAB:
    ollama_status = get_ollama_status()
    with summary_action_slot.container():
        render_ollama_prompt(ollama_status)
        generate_clicked = render_summary_button(
            disabled=(
                not has_checked_emails()
                or st.session_state.summary_processing
                or not ollama_status["model_ready"]
            )
        )
    with summary_filter_slot.container():
        source_for_filter = (
            st.session_state.search_results
            if st.session_state.search_active else st.session_state.emails
        )
        render_inbox_filters(source_for_filter)
    inbox_actions, list_source = render_inbox_tab(activity_slot, folder=FOLDER)
    if generate_clicked:
        if start_summary_generation(list_source, folder=FOLDER):
            st.rerun()

    handle_inbox_actions(inbox_actions, activity_slot, folder=FOLDER)
else:
    summary_action_slot.empty()
    with summary_filter_slot.container():
        render_summary_filters(st.session_state.summaries)
    render_summary_tab()
