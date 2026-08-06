import streamlit as st

from storage.email_store import EmailStore, normalize_account_email
from storage.session_store import get_session
from storage.summary_store import SummaryStore


# Add a default only when the session key does not exist.
def _init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


# Prepare the Streamlit session values used by the app.
def initialize_session_state():
    defaults = {
        "logged_in": False,
        "emails": [],
        "selected_uid": None,
        "inbox_loaded": False,
        "inbox_offset": 0,
        "inbox_has_more": False,
        "inbox_total": 0,
        "email_bodies": {},
        "email_validation_cache": {},
        "checked_uids": set(),
        "search_active": False,
        "search_results": [],
        "search_total": 0,
        "full_synced": False,
        "full_sync_attempted": False,
        "loading": False,
        "inbox_search_submit": False,
        "inbox_search_clear": False,
        "last_mail_check": 0.0,
        "new_mail_count": 0,
        "email_deletion_notice": "",
        "summaries": [],
        "selected_summary_uid": None,
        "summary_processing": False,
        "summary_future": None,
        "summary_job_uids": [],
        "summary_progress": None,
        "open_summary_tab": False,
        "active_workspace": "inbox",
        "summary_filter": "all",
        "summary_arrange_by": None,
        "summary_sort_order": None,
        "summary_filter_popover_version": 0,
        "summary_offset": 0,
        "summary_page_size": 50,
        "switch_to_summary": False,
        "clear_checked_after_summary": [],
        "clear_checked_after_refresh": [],
        "new_email_uids": set(),
        "inbox_filter": "all",
        "inbox_arrange_by": None,
        "inbox_sort_order": None,
        "inbox_filter_popover_version": 0,
        "login_authenticating": False,
        "login_error": "",
        "login_email_error": "",
        "post_login_loading": False,
        "login_submit_requested": False,
        "login_manual_mode": False,
        "suppress_login_autofill": True,
        "pending_login_email": "",
        "pending_login_password": "",
        "pending_login_server": "",
        "pending_login_port": 993,
        "microsoft_login_active": False,
        "microsoft_login_error": "",
        "microsoft_login_redirect_url": "",
        "profile_image_url": "",
    }
    for key, default in defaults.items():
        _init_state(key, default)


# Clear inbox, search, and reader state after an account change.
def _reset_mailbox_state_for_account():
    defaults = {
        "emails": [],
        "selected_uid": None,
        "inbox_loaded": False,
        "inbox_offset": 0,
        "inbox_has_more": False,
        "inbox_total": 0,
        "email_bodies": {},
        "email_validation_cache": {},
        "checked_uids": set(),
        "search_active": False,
        "search_results": [],
        "search_total": 0,
        "full_synced": False,
        "full_sync_attempted": False,
        "loading": False,
        "last_mail_check": 0.0,
        "new_mail_count": 0,
        "email_deletion_notice": "",
        "summaries": [],
        "selected_summary_uid": None,
        "summary_processing": False,
        "summary_future": None,
        "summary_job_uids": [],
        "summary_progress": None,
        "open_summary_tab": False,
        "active_workspace": "inbox",
        "summary_filter": "all",
        "summary_arrange_by": None,
        "summary_sort_order": None,
        "summary_filter_popover_version": 0,
        "summary_offset": 0,
        "summary_page_size": 50,
        "switch_to_summary": False,
        "clear_checked_after_summary": [],
        "clear_checked_after_refresh": [],
        "new_email_uids": set(),
        "inbox_filter": "all",
        "inbox_arrange_by": None,
        "inbox_sort_order": None,
        "inbox_filter_popover_version": 0,
        "login_authenticating": False,
        "login_error": "",
        "login_email_error": "",
        "post_login_loading": False,
        "login_submit_requested": False,
        "login_manual_mode": False,
        "suppress_login_autofill": True,
        "pending_login_email": "",
        "pending_login_password": "",
        "pending_login_server": "",
        "pending_login_port": 993,
        "microsoft_login_active": False,
        "microsoft_login_error": "",
        "microsoft_login_redirect_url": "",
        "profile_image_url": "",
    }
    for key, value in defaults.items():
        st.session_state[key] = value


# Bind the shared database store to the signed-in email account.
def bind_store_to_signed_in_account():
    account_email = normalize_account_email(
        st.session_state.get("email_address", "")
    )
    current_store = st.session_state.get("email_store")
    current_summary_store = st.session_state.get("summary_store")

    if (
        current_store is not None
        and current_store.account_email == account_email
        and current_summary_store is not None
        and current_summary_store.account_email == account_email
    ):
        return

    if current_store is not None:
        try:
            current_store.close()
        except Exception:
            pass
    if current_summary_store is not None:
        try:
            current_summary_store.close()
        except Exception:
            pass

    _reset_mailbox_state_for_account()
    st.session_state.email_store = EmailStore(account_email=account_email)
    st.session_state.summary_store = SummaryStore(account_email=account_email)
    st.session_state.active_store_account = account_email
    st.session_state.summaries = st.session_state.summary_store.load_all("INBOX")
    if st.session_state.summaries:
        st.session_state.selected_summary_uid = st.session_state.summaries[0]["uid"]


# Restore the live login after a browser refresh.
def restore_saved_session():
    if not st.session_state.logged_in:
        token = st.query_params.get("s")
        saved = get_session(token)
        if saved:
            st.session_state.imap_client = saved["client"]
            st.session_state.logged_in = True
            st.session_state.email_address = saved["email_address"]
            st.session_state.session_token = token
            st.session_state.post_login_loading = True
        elif token:
            st.query_params.clear()
