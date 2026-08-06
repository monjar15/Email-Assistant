"""
Sidebar UI: legacy IMAP login helper, logout button, and account status.

Scope note: the current full-page login lives in ui/login.py. This legacy
sidebar helper keeps the same provider-detection behavior for compatibility.
"""
import html as html_lib

import streamlit as st

from email_handler.provider_detect import detect_provider
from services.auth_service import login, logout
from storage.session_store import create_session, delete_session
from ui.markup import section_label
from ui.summary_metrics import summary_overview_counts


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

    provider_not_found = bool(
        detection and not detection.get("supported")
    )
    if provider_not_found:
        st.error("Couldn't find this account")

    password = st.text_input(
        "Password", type="password", key="login_password",
        placeholder="App password or account password",
    )

    st.caption(
        "Outlook/Hotmail accounts must use Continue with Microsoft on the "
        "main login page. Gmail, Yahoo, and some other providers may require "
        "an app password when 2-factor authentication is enabled."
    )

    login_clicked = st.button("Login", key="login_button", type="primary", use_container_width=True)

    if login_clicked:
        with st.spinner("Connecting..."):
            if detection and detection["supported"]:
                result = login(email_address, password)
            elif provider_not_found:
                result = {
                    "success": False,
                    "error": "Couldn't find this account",
                }
            else:
                result = {
                    "success": False,
                    "error": "Enter a valid email address to continue.",
                }

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
    if st.button("↪ Logout", key="logout_button", use_container_width=True):
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
            "summary_arrange_by", "summary_sort_order",
            "summary_filter_popover_version", "summary_offset",
            "summary_page_size",
            "switch_to_summary",
            "clear_checked_after_summary", "new_email_uids",
            "clear_checked_after_refresh",
            "inbox_filter",
            "login_authenticating", "login_error", "login_email_error",
            "post_login_loading",
            "login_submit_requested", "login_manual_mode",
            "suppress_login_autofill",
            "login_email", "login_password", "login_server", "login_port",
            "pending_login_email", "pending_login_password",
            "pending_login_server", "pending_login_port",
            "microsoft_login_active", "microsoft_login_error",
            "microsoft_login_redirect_url",
            "profile_image_url",
        ]:
            st.session_state.pop(key, None)

        # Remove cached provider-detection results as part of the clean logout.
        for key in list(st.session_state.keys()):
            if key.startswith("detect::"):
                st.session_state.pop(key, None)

        # Keep the signed-out form blank even when the browser has saved
        # credentials. This flag only affects the login page after logout.
        st.session_state.suppress_login_autofill = True
        st.session_state.login_manual_mode = False
        st.session_state.login_email_error = ""
        st.rerun()


# Show a compact signed-in account card.
def render_status():
    email_address = str(st.session_state.get("email_address", "") or "")
    profile_image_url = str(st.session_state.get("profile_image_url", "") or "").strip()

    # IMAP does not provide an account profile picture. This hook displays
    # the real image when an OAuth-based login later supplies one; otherwise
    # use a neutral user icon instead of showing a misleading initial/number.
    if profile_image_url.startswith(("https://", "http://", "data:image/")):
        avatar_markup = (
            f'<img src="{html_lib.escape(profile_image_url, quote=True)}" '
            'alt="Account profile picture" referrerpolicy="no-referrer">'
        )
    else:
        avatar_markup = """
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="8" r="3.5"></circle>
                <path d="M5.5 19c.8-3.5 3-5.2 6.5-5.2s5.7 1.7 6.5 5.2"></path>
            </svg>
        """

    st.markdown(
        f"""
        <div class="sidebar-account-card">
            <div class="sidebar-account-avatar">{avatar_markup}</div>
            <div class="sidebar-account-copy">
                <div class="sidebar-account-label">Signed in as</div>
                <div class="sidebar-account-email" title="{html_lib.escape(email_address, quote=True)}">
                    {html_lib.escape(email_address)}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_button(disabled: bool = False) -> bool:
    """Render the inbox action that starts a new summary request."""
    st.markdown(section_label("AI Tools"), unsafe_allow_html=True)

    # has_checked_emails() synchronizes this set immediately before
    # the sidebar action is rendered.
    selected_count = len(st.session_state.get("checked_uids", set()))

    clicked = st.button(
        "Generate Summary",
        key="generate_summary_button",
        use_container_width=True,
        disabled=disabled,
    )

    if selected_count > 0:
        noun = "email" if selected_count == 1 else "emails"
        st.markdown(
            f'<div class="sidebar-selection-note">{selected_count} {noun} selected</div>',
            unsafe_allow_html=True,
        )

    return clicked


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
    """Render AI Summary-only filter controls in compact counted rows."""
    counts = {
        "all": len(summaries),
        "unread": sum(not item.get("is_read", False) for item in summaries),
        "high": sum(item.get("priority", "").casefold() == "high" for item in summaries),
    }
    st.markdown(section_label("Summary Filters"), unsafe_allow_html=True)
    active = st.session_state.get("summary_filter", "all")

    for filter_key, icon, label in [
        ("all", "☷", "All Summaries"),
        ("unread", "✉", "Unread"),
        ("high", "⚑", "High Priority"),
    ]:
        with st.container(key=f"sidebar_filter_row_summary_{filter_key}"):
            clicked = st.button(
                f"{icon}  {label}",
                key=f"sidebar_filter_{filter_key}",
                type="primary" if active == filter_key else "secondary",
                use_container_width=True,
            )
            st.markdown(
                f'<span class="sidebar-filter-count">{counts[filter_key]:,}</span>',
                unsafe_allow_html=True,
            )
            if clicked:
                st.session_state.summary_filter = filter_key
                st.rerun()


def render_inbox_filters(emails: list[dict]):
    """Render Inbox-only filters using compact aligned sidebar rows."""
    unread_uids = st.session_state.get("new_email_uids", set())
    counts = {
        "all": st.session_state.get("inbox_total", len(emails)),
        "unread": sum(str(item.get("uid")) in unread_uids for item in emails),
    }
    st.divider()
    st.markdown(section_label("Filters"), unsafe_allow_html=True)
    active = st.session_state.get("inbox_filter", "all")

    for filter_key, icon, label in [
        ("all", "☷", "All Inboxes"),
        ("unread", "✉", "Unread"),
    ]:
        with st.container(key=f"sidebar_filter_row_{filter_key}"):
            clicked = st.button(
                f"{icon}  {label}",
                key=f"sidebar_inbox_filter_{filter_key}",
                type="primary" if active == filter_key else "secondary",
                use_container_width=True,
            )
            st.markdown(
                f'<span class="sidebar-filter-count">{counts[filter_key]:,}</span>',
                unsafe_allow_html=True,
            )
            if clicked:
                st.session_state.inbox_filter = filter_key
                st.rerun()



def _set_summary_overview_filter(filter_key: str):
    """Apply one sidebar summary filter and reset the list position."""
    st.session_state.summary_filter = filter_key
    st.session_state.summary_offset = 0
    st.session_state.selected_summary_uid = None


def render_summary_overview(summaries: list[dict]):
    """Show counted priority and task-status rows in the AI Summary sidebar."""
    counts = summary_overview_counts(summaries)
    active = st.session_state.get("summary_filter", "all")

    st.markdown('<div class="sidebar-overview-divider"></div>', unsafe_allow_html=True)
    st.markdown(section_label("Summary Overview"), unsafe_allow_html=True)

    groups = [
        (
            "Priority",
            [
                ("high", "🔴", "High Priority", "priority_high"),
                ("priority_medium", "🟠", "Medium Priority", "priority_medium"),
                ("priority_low", "🟢", "Low Priority", "priority_low"),
            ],
        ),
        (
            "Status",
            [
                ("status_complete", "✓", "Complete", "status_complete"),
                ("status_in_progress", "●", "In Progress", "status_in_progress"),
                ("status_pending", "◷", "Pending", "status_pending"),
            ],
        ),
        (
            "Deadline",
            [
                ("deadline_today", "📅", "Today", "deadline_today"),
                ("deadline_week", "🗓️", "This Week", "deadline_week"),
                ("deadline_month", "📆", "This Month", "deadline_month"),
            ],
        ),
    ]

    for group_name, rows in groups:
        # Each group can be minimized/maximized independently while retaining
        # Streamlit's accessible keyboard and screen-reader behavior.
        with st.expander(group_name, expanded=True):
            for filter_key, icon, label, count_key in rows:
                with st.container(key=f"sidebar_filter_row_summary_overview_{filter_key}"):
                    clicked = st.button(
                        f"{icon}  {label}" if icon else label,
                        key=f"sidebar_summary_overview_{filter_key}",
                        type="primary" if active == filter_key else "secondary",
                        use_container_width=True,
                    )
                    st.markdown(
                        f'<span class="sidebar-filter-count">{counts[count_key]:,}</span>',
                        unsafe_allow_html=True,
                    )
                    if clicked:
                        _set_summary_overview_filter(filter_key)
                        st.rerun()
