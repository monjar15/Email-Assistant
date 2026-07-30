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


FILTER_BUTTON_TEXT_COLUMNS = 21

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
        "Many providers (Gmail, Outlook, Yahoo) require a generated "
        "app password rather than your normal account password when "
        "2-factor authentication is enabled."
    )

    login_clicked = st.button("Login", key="login_button", type="primary", use_container_width=True)

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
    if st.button("Logout", key="logout_button", use_container_width=True):
        logout(st.session_state.get("imap_client"))
        delete_session(st.session_state.get("session_token"))
        email_store = st.session_state.get("email_store")
        if email_store is not None:
            try:
                email_store.close()
            except Exception:
                pass
        summary_store = st.session_state.get("summary_store")
        if summary_store is not None:
            try:
                summary_store.close()
            except Exception:
                pass
        st.query_params.clear()
        for key in [
            "imap_client", "logged_in", "email_address", "session_token",
            "email_store", "summary_store", "active_store_account",
            "selected_uid", "emails", "inbox_loaded", "email_bodies",
            "inbox_offset", "inbox_total", "inbox_has_more", "loading",
            "last_mail_check", "new_mail_count", "checked_uids",
            "search_active", "search_results", "search_total",
            "full_synced", "full_sync_attempted", "inbox_search_query",
            "inbox_search_submit", "inbox_search_clear",
            "summaries", "selected_summary_uid", "summary_processing", "open_summary_tab",
            "summary_future", "summary_job_uids", "summary_executor",
            "summary_progress",
            "active_workspace", "summary_filter", "summary_search_query",
            "switch_to_summary",
            "clear_checked_after_summary", "new_email_uids",
            "clear_checked_after_refresh",
            "inbox_filter",
        ]:
            st.session_state.pop(key, None)
        st.rerun()


# Show the signed-in email address.
def render_status():
    st.markdown(section_label("Signed In As"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="item-meta" style="margin-bottom: 0.8rem;">{st.session_state.get("email_address", "")}</div>',
        unsafe_allow_html=True,
    )


def render_summary_button(disabled: bool = False) -> bool:
    """Render the inbox action that starts a new summary request."""
    st.markdown(section_label("AI Tools"), unsafe_allow_html=True)
    return st.button(
        "Generate Summary",
        key="generate_summary_button",
        use_container_width=True,
        disabled=disabled,
    )


def render_ollama_prompt(ollama_status: dict):
    """Explain the manual local setup needed for summaries; never installs it."""
    if not ollama_status["available"]:
        st.warning("AI summaries need Ollama to be installed and running locally.")
        st.caption("Install Ollama manually, then start it. The app will not download or install it for you.")
        return

    if not ollama_status["model_ready"]:
        st.warning("The local Qwen3 model is not available yet.")
        st.code("ollama pull qwen3:1.7b", language="bash")
        st.caption("Run this command yourself to download the model. The app will not run it automatically.")


def render_summary_filters(summaries: list[dict]):
    """Render AI Summary-only filter controls in the sidebar."""
    counts = {
        "all": len(summaries),
        "unread": sum(not item.get("is_read", False) for item in summaries),
        "high": sum(item.get("priority", "").casefold() == "high" for item in summaries),
    }
    st.markdown(section_label("Summary Filters"), unsafe_allow_html=True)
    active = st.session_state.get("summary_filter", "all")

    def filter_button_label(icon: str, label: str, count: int) -> str:
        """Create fixed-width text so every count ends at the right edge."""
        count_text = str(count)
        used_columns = 2 + len(label) + len(count_text)  # icon, space, label, count
        spacer = "\u2007" * max(1, FILTER_BUTTON_TEXT_COLUMNS - used_columns)
        return f"{icon} {label}{spacer}{count_text}"

    for filter_key, icon, label in [
        ("all", "☷", "All Summaries"),
        ("unread", "✉", "Unread"),
        ("high", "⚑", "High Priority"),
    ]:
        if st.button(
            filter_button_label(icon, label, counts[filter_key]),
            key=f"sidebar_filter_{filter_key}",
            type="primary" if active == filter_key else "secondary",
            use_container_width=True,
        ):
            st.session_state.summary_filter = filter_key
            st.rerun()


def render_inbox_filters(emails: list[dict]):
    """Render Inbox-only filters using the same compact sidebar treatment."""
    unread_uids = st.session_state.get("new_email_uids", set())
    counts = {
        "all": st.session_state.get("inbox_total", len(emails)),
        "unread": sum(str(item.get("uid")) in unread_uids for item in emails),
    }
    st.divider()
    st.markdown(section_label("Inbox Filters"), unsafe_allow_html=True)
    active = st.session_state.get("inbox_filter", "all")

    def button_label(icon: str, label: str, count: int) -> str:
        padding = "\u2007" * max(1, 19 - len(label) - len(str(count)))
        return f"{icon} {label}{padding}{count}"

    for filter_key, icon, label in [
        ("all", "☷", "All Inboxes"),
        ("unread", "✉", "Unread"),
    ]:
        if st.button(
            button_label(icon, label, counts[filter_key]),
            key=f"sidebar_inbox_filter_{filter_key}",
            type="primary" if active == filter_key else "secondary",
            use_container_width=True,
        ):
            st.session_state.inbox_filter = filter_key
            st.rerun()
