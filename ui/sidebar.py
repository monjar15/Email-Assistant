"""
Sidebar UI: universal IMAP login form, logout button, and account status.

Scope note: on login, the email's domain is auto-detected against
KNOWN_PROVIDERS or live IMAP autodiscovery (see
email_handler/provider_detect.py). If detection fails, the user can
supply server/port manually instead of being blocked.
"""
import streamlit as st

from email_handler.provider_detect import detect_provider
from services.auth_service import login, logout
from storage.session_store import create_session, delete_session
from ui.styles import section_label


def render_login_form():
    # Render the universal IMAP login form.
    st.markdown(section_label("Email Login"), unsafe_allow_html=True)

    email_address = st.text_input(
        "Email address", key="login_email", placeholder="you@example.com"
    )

    detection = None
    if email_address and "@" in email_address:
        cache_key = f"detect::{email_address.lower()}"
        if cache_key not in st.session_state:
            with st.spinner("Checking your email provider..."):
                st.session_state[cache_key] = detect_provider(email_address)
        detection = st.session_state[cache_key]

    manual_server, manual_port = None, None
    if detection and detection["supported"]:
        pass
    elif detection and not detection["supported"]:
        st.warning(
            "We couldn't automatically detect IMAP settings for this address. "
            "Enter your provider's IMAP server and port manually below."
        )
        col1, col2 = st.columns([3, 1])
        manual_server = col1.text_input("IMAP server", key="login_server", placeholder="imap.example.com")
        manual_port = col2.number_input("Port", key="login_port", value=993, step=1)

    password = st.text_input(
        "Password", type="password", key="login_password",
        placeholder="App password or account password",
    )

    st.caption(
        "Many providers (Gmail, Outlook, Yahoo, iCloud) require a generated "
        "app password rather than your normal account password when "
        "2-factor authentication is enabled."
    )

    login_clicked = st.button("Login", type="primary", use_container_width=True)

    if login_clicked:
        with st.spinner("Connecting..."):
            if detection and detection["supported"]:
                result = login(email_address, password)
            elif manual_server:
                result = login(email_address, password, server=manual_server, port=int(manual_port))
            else:
                result = {"success": False, "error": "Enter a valid email address to continue."}

        if result["success"]:
            token = create_session(result["client"], email_address)
            st.session_state.imap_client = result["client"]
            st.session_state.logged_in = True
            st.session_state.email_address = email_address
            st.session_state.session_token = token
            st.query_params["s"] = token
            st.rerun()
        else:
            st.error(result["error"])


# Render logout and clear the current account state.
def render_logout_button():
    if st.button("Logout", use_container_width=True):
        logout(st.session_state.get("imap_client"))
        delete_session(st.session_state.get("session_token"))
        email_store = st.session_state.get("email_store")
        if email_store is not None:
            try:
                email_store.close()
            except Exception:
                pass
        st.query_params.clear()
        for key in [
            "imap_client", "logged_in", "email_address", "session_token",
            "email_store", "active_store_account",
            "selected_uid", "emails", "inbox_loaded", "email_bodies",
            "inbox_offset", "inbox_total", "inbox_has_more", "loading",
            "last_mail_check", "new_mail_count", "checked_uids",
            "search_active", "search_results", "search_total",
            "full_synced", "full_sync_attempted", "inbox_search_query",
            "inbox_search_submit", "inbox_search_clear",
        ]:
            st.session_state.pop(key, None)
        st.rerun()


# Show the signed-in email address.
def render_status():
    st.divider()
    st.markdown(section_label("Signed In As"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="item-meta" style="margin-bottom: 0.8rem;">{st.session_state.get("email_address", "")}</div>',
        unsafe_allow_html=True,
    )
