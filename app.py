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
from ui.login import render_loading_page, render_login_page
from ui.sidebar import (
    render_logout_button,
    render_ollama_prompt,
    render_status,
    render_summary_button,
    render_summary_overview,
)
from ui.markup import sidebar_brand
from ui.styles import load_styles
from ui.tabs.inbox_tab import render_inbox_tab
from ui.tabs.navigation import INBOX_TAB, SUMMARY_TAB, TODO_TAB, render_sidebar_navigation
from ui.tabs.summary_tab import render_summary_tab
from ui.tabs.todo_tab import render_todo_tab

st.set_page_config(
    page_title="MailMind AI — Email Assistant",
    page_icon="✒",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_styles()

initialize_session_state()

NEW_MAIL_CHECK_SECONDS = 30
WORKSPACE_HEIGHT = 700
FOLDER = "INBOX"

# Restore a live server-side login after a browser refresh.
restore_saved_session()


def render_app_sidebar():
    """Render a stable sidebar in every application state."""
    summary_action_slot = None
    summary_filter_slot = None
    activity_slot = None

    with st.sidebar:
        with st.container(key="sidebar_shell"):
            with st.container(key="sidebar_header"):
                st.markdown(
                    sidebar_brand("MailMind AI", "AI-Assisted Inbox &amp; Task Management"),
                    unsafe_allow_html=True,
                )
            with st.container(key="sidebar_body"):
                if st.session_state.logged_in:
                    render_sidebar_navigation()
                    summary_action_slot = st.empty()
                    summary_filter_slot = st.empty()
                    activity_slot = st.empty()
                else:
                    st.markdown(
                        '<div class="sidebar-signed-out-note">Sign in to open your inbox and tools.</div>',
                        unsafe_allow_html=True,
                    )
            if st.session_state.logged_in:
                with st.container(key="sidebar_footer"):
                    render_status()
                    render_logout_button()

    return summary_action_slot, summary_filter_slot, activity_slot


if not st.session_state.logged_in:
    render_login_page()
    st.stop()

# The application sidebar belongs to the signed-in workspace only. Rendering it
# after the login guard keeps the sign-in page full-width and distraction-free.
summary_action_slot, summary_filter_slot, activity_slot = render_app_sidebar()

if st.session_state.get("post_login_loading"):
    render_loading_page(
        title="Loading your inbox",
        subtitle="Please wait while your mailbox is being prepared.",
    )
    # Keep the full-page inbox loader visible until the inbox is ready.
    # Do not render the separate "Checking mailbox status" activity bar.
    bind_store_to_signed_in_account()
    load_inbox_if_needed(None, folder=FOLDER)
    run_full_sync_if_needed(None, folder=FOLDER)
    st.session_state.post_login_loading = False
    st.rerun()

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
if st.session_state.active_workspace not in {INBOX_TAB, SUMMARY_TAB, TODO_TAB}:
    st.session_state.active_workspace = INBOX_TAB
active_workspace = st.session_state.active_workspace

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
    summary_filter_slot.empty()
    inbox_actions, list_source = render_inbox_tab(activity_slot, folder=FOLDER)
    if generate_clicked:
        if start_summary_generation(list_source, folder=FOLDER):
            st.rerun()

    handle_inbox_actions(inbox_actions, activity_slot, folder=FOLDER)
elif active_workspace == SUMMARY_TAB:
    summary_action_slot.empty()
    with summary_filter_slot.container():
        render_summary_overview(st.session_state.summaries)
    render_summary_tab()
else:
    summary_action_slot.empty()
    summary_filter_slot.empty()
    render_todo_tab()
