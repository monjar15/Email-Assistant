import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from config import MAX_EMAILS_FETCH
from services.email_service import refresh_inbox_conversations, get_full_email, sync_all_inbox, search_inbox
from storage.email_store import EmailStore
from services.session_store import get_session
from ui.sidebar import render_login_form, render_logout_button, render_status
from ui.inbox import render_inbox
from ui.reader import render_reader
from ui.styles import get_css, brand_header
from email_handler.email_threading import supports_gmail_threading

st.set_page_config(page_title="MailMind AI \u2014 Email Assistant", page_icon="\u2712", layout="wide")
st.markdown(get_css(), unsafe_allow_html=True)

if "email_store" not in st.session_state:
    st.session_state.email_store = EmailStore()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "emails" not in st.session_state:
    st.session_state.emails = []
if "selected_uid" not in st.session_state:
    st.session_state.selected_uid = None
if "inbox_loaded" not in st.session_state:
    st.session_state.inbox_loaded = False
if "inbox_offset" not in st.session_state:
    st.session_state.inbox_offset = 0
if "inbox_offset_stack" not in st.session_state:
    st.session_state.inbox_offset_stack = [0]
if "inbox_has_more" not in st.session_state:
    st.session_state.inbox_has_more = False
if "inbox_raw_consumed" not in st.session_state:
    st.session_state.inbox_raw_consumed = 0
if "inbox_total" not in st.session_state:
    st.session_state.inbox_total = 0
if "inbox_conv_offset_stack" not in st.session_state:
    st.session_state.inbox_conv_offset_stack = [0]
if "inbox_conv_ratio_raw_sum" not in st.session_state:
    st.session_state.inbox_conv_ratio_raw_sum = 0
if "inbox_conv_ratio_conv_sum" not in st.session_state:
    st.session_state.inbox_conv_ratio_conv_sum = 0
if "inbox_total_conversations" not in st.session_state:
    st.session_state.inbox_total_conversations = None
if "email_bodies" not in st.session_state:
    st.session_state.email_bodies = {}
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "selected_thread_id" not in st.session_state:
    st.session_state.selected_thread_id = None
if "checked_uids" not in st.session_state:
    st.session_state.checked_uids = set()
if "search_active" not in st.session_state:
    st.session_state.search_active = False
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "full_synced" not in st.session_state:
    st.session_state.full_synced = False
if "loading" not in st.session_state:
    st.session_state.loading = False
if "pending_action" not in st.session_state:
    st.session_state.pending_action = None
if "pending_offset" not in st.session_state:
    st.session_state.pending_offset = 0

NEW_MAIL_CHECK_SECONDS = 30
if "last_mail_check" not in st.session_state:
    st.session_state.last_mail_check = 0.0
if "new_mail_count" not in st.session_state:
    st.session_state.new_mail_count = 0

# --------------------------------------------------------------------------
# Resume a login that already happened, after a browser refresh.
# --------------------------------------------------------------------------
if not st.session_state.logged_in:
    token = st.query_params.get("s")
    saved = get_session(token)
    if saved:
        st.session_state.imap_client = saved["client"]
        st.session_state.logged_in = True
        st.session_state.email_address = saved["email_address"]
        st.session_state.session_token = token
    elif token:
        # Unknown/expired token (e.g. the server restarted) — drop it
        # quietly instead of getting stuck trying to reuse it.
        st.query_params.clear()

st.markdown(
    brand_header("MailMind AI", "AI-Assisted Inbox &amp; Task Management"),
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Login to Gmail (IMAP)
# --------------------------------------------------------------------------
info_slot = st.empty()
login_slot = st.sidebar.empty()
status_slot = st.sidebar.empty()

if not st.session_state.logged_in:
    with info_slot.container():
        st.info("Log in with your Gmail account from the sidebar to get started.")
    with login_slot.container():
        render_login_form()
    st.stop()

with status_slot.container():
    render_logout_button()
    render_status()

# --------------------------------------------------------------------------
# Retrieve inbox (IMAP) — auto-fetch page 1 right after login, no manual
# "Refresh Inbox" click needed the first time.
# --------------------------------------------------------------------------
if not st.session_state.inbox_loaded:
    with st.spinner("Fetching inbox..."):
        client = st.session_state.imap_client
        result = refresh_inbox_conversations(client, limit=MAX_EMAILS_FETCH, offset=0,
                                              store=st.session_state.email_store)
    st.session_state.inbox_loaded = True
    if result["success"]:
        st.session_state.emails = result["emails"]
        st.session_state.conversations = result.get("conversations", [])
        st.session_state.inbox_total = result["total"]
        st.session_state.inbox_offset = 0
        st.session_state.inbox_offset_stack = [0]
        st.session_state.inbox_conv_offset_stack = [0]
        st.session_state.inbox_conv_ratio_raw_sum = len(result["emails"])
        st.session_state.inbox_conv_ratio_conv_sum = len(result.get("conversations", []))
        st.session_state.inbox_has_more = result.get("has_more", False)
        st.session_state.inbox_raw_consumed = result.get("raw_consumed", len(result["emails"]))
        if "store_error" in result:
            print(f"[app] DB save failed on initial fetch: {result['store_error']}", flush=True)
    else:
        st.error(f"Could not fetch inbox: {result['error']}")

# --------------------------------------------------------------------------
# Automatic full-mailbox sync — runs the FIRST time ever, right after the
# page-1 fetch above, so the local SQLite cache ends up holding the
# ENTIRE mailbox rather than just whatever pages the user happens to
# browse to (see email_service.sync_all_inbox).
# --------------------------------------------------------------------------
if st.session_state.inbox_loaded and not st.session_state.full_synced:
    cached_total = st.session_state.email_store.get_page("INBOX", limit=1, offset=0)["total"]
    already_synced = (
        st.session_state.inbox_total > 0
        and cached_total >= st.session_state.inbox_total
    )

    if already_synced:
        st.session_state.full_synced = True
    else:
        sync_progress = st.progress(0.0, text="Syncing all emails...")

        def _update_sync_progress(synced, total):
            frac = min(synced / total, 1.0) if total else 0.0
            sync_progress.progress(frac, text=f"Syncing all emails... {synced} / {total or '?'}")

        sync_result = sync_all_inbox(
            st.session_state.imap_client,
            st.session_state.email_store,
            progress_callback=_update_sync_progress,
        )
        sync_progress.empty()
        st.session_state.full_synced = True
        if not sync_result["success"]:
            print(f"[app] Full sync stopped after {sync_result['synced']} email(s): "
                  f"{sync_result['error']}", flush=True)

if st.session_state.full_synced and st.session_state.inbox_total_conversations is None:
    st.session_state.inbox_total_conversations = st.session_state.email_store.get_conversation_count(
        "INBOX", supports_gmail_threading(st.session_state.email_address)
    )
# --------------------------------------------------------------------------
# New-mail check (throttled) — see the NEW_MAIL_CHECK_SECONDS comment
# above. Skipped while a fetch is already in flight so it never adds an
# extra round-trip on top of one that's about to update inbox_total
# anyway.
# --------------------------------------------------------------------------
if (
    st.session_state.inbox_loaded
    and not st.session_state.loading
    and (time.time() - st.session_state.last_mail_check) > NEW_MAIL_CHECK_SECONDS
):
    st.session_state.last_mail_check = time.time()
    current_count = st.session_state.imap_client.get_message_count()
    if current_count is not None and current_count > st.session_state.inbox_total:
        st.session_state.new_mail_count = current_count - st.session_state.inbox_total
    else:
        st.session_state.new_mail_count = 0

if st.session_state.new_mail_count > 0:
    st.info(
        f"\U0001F4E5 {st.session_state.new_mail_count} new message"
        f"{'s' if st.session_state.new_mail_count != 1 else ''} — "
        f"click the refresh icon in the inbox list to load them."
    )

# --------------------------------------------------------------------------
# 40% email list (scrollable) / 60% selected email content, side by side
# --------------------------------------------------------------------------
col_list, col_content = st.columns([0.4, 0.6], gap="large")

with col_list:
    list_source = st.session_state.search_results if st.session_state.search_active else st.session_state.emails
    conversations_source = None if st.session_state.search_active else st.session_state.conversations
    inbox_actions = render_inbox(
        list_source,
        total=st.session_state.inbox_total,
        offset=st.session_state.inbox_offset,
        limit=MAX_EMAILS_FETCH,
        loading=st.session_state.loading,
        checked_uids=st.session_state.checked_uids,
        search_active=st.session_state.search_active,
        conversations=conversations_source,
        can_prev=len(st.session_state.inbox_offset_stack) > 1,
        can_next=st.session_state.inbox_has_more,
        conv_offset=st.session_state.inbox_conv_offset_stack[-1],
        total_conversations=(
            st.session_state.inbox_total_conversations
            if st.session_state.inbox_total_conversations is not None
            else (
                round(
                    st.session_state.inbox_total
                    * st.session_state.inbox_conv_ratio_conv_sum
                    / st.session_state.inbox_conv_ratio_raw_sum
                )
                if st.session_state.inbox_conv_ratio_raw_sum else st.session_state.inbox_total
            )
        ),
        total_conversations_is_estimate=(st.session_state.inbox_total_conversations is None),
    )
    st.session_state.checked_uids = inbox_actions["checked_uids"]

with col_content:
    selected_conv = None
    if not st.session_state.search_active:
        selected_conv = next(
            (c for c in st.session_state.conversations
             if c["thread_id"] == st.session_state.selected_thread_id),
            None,
        )

    def _load_message(uid, header, folder="INBOX"):
        cache_key = (folder, uid)
        if cache_key not in st.session_state.email_bodies:
            client = st.session_state.imap_client
            body_result = get_full_email(client, uid, folder=folder, store=st.session_state.email_store)
            if body_result["success"]:
                st.session_state.email_bodies[cache_key] = body_result["email"]
                if "store_error" in body_result:
                    print(f"[app] DB save failed on message open: {body_result['store_error']}", flush=True)
            else:
                st.error(f"Could not load email: {body_result['error']}")
        full = st.session_state.email_bodies.get(cache_key, header)
        atts = full.get("attachments")
        if atts is None:
            atts = st.session_state.email_store.get_attachments(folder, uid)
        return {"email": full, "attachments": atts or []}

    thread_messages = []
    if selected_conv is not None:
        all_uids = selected_conv.get("all_uids") or [m["uid"] for m in selected_conv["emails"]]
        thread_folder = selected_conv.get("all_mail_folder") or "INBOX"
        if selected_conv.get("all_mail_folder"):
            headers_by_uid = {}
        else:
            headers_by_uid = {m["uid"]: m for m in selected_conv["emails"]}

        spinner_text = "Loading conversation..." if len(all_uids) > 1 else "Loading email..."
        with st.spinner(spinner_text):
            for uid in all_uids:
                header = headers_by_uid.get(uid) or {
                    "uid": uid, "subject": selected_conv["subject"], "from": "", "date_display": "",
                }
                thread_messages.append(_load_message(uid, header, folder=thread_folder))

        def _uid_sort_key(msg):
            try:
                return int(msg["email"].get("uid", 0))
            except (TypeError, ValueError):
                return 0
        thread_messages.sort(key=_uid_sort_key, reverse=True)
    else:
        # Search results (or nothing selected) aren't grouped into
        # conversations — same single-message behavior as before.
        selected_header = next(
            (e for e in list_source if e["uid"] == st.session_state.selected_uid),
            None,
        )
        if selected_header:
            with st.spinner("Loading email..."):
                thread_messages.append(_load_message(selected_header["uid"], selected_header))

    render_reader(thread_messages)

# --------------------------------------------------------------------------
# Pagination actions — each one replaces the current page (Gmail-style),
# it never appends. "Refresh" always jumps back to page 1, since that's
# where any newly-arrived mail would show up.
# --------------------------------------------------------------------------
query = (inbox_actions["query"] or "").strip()
if inbox_actions["search"] and query:
    result = search_inbox(st.session_state.email_store, query)
    if result["success"]:
        st.session_state.search_results = result["emails"]
        st.session_state.search_active = True
    else:
        st.error(f"Search failed: {result['error']}")
    st.rerun()

if inbox_actions["clear_search"]:
    st.session_state.search_active = False
    st.session_state.search_results = []
    st.rerun()

if not st.session_state.loading:
    if inbox_actions["refresh"]:
        st.session_state.search_active = False
        st.session_state.search_results = []
        st.session_state.loading = True
        st.session_state.pending_action = "refresh"
        st.session_state.pending_offset = 0
        st.rerun()

    elif inbox_actions["next"]:
        st.session_state.loading = True
        st.session_state.pending_action = "next"
        st.session_state.pending_offset = (
            st.session_state.inbox_offset + st.session_state.inbox_raw_consumed
        )
        st.rerun()

    elif inbox_actions["prev"] and len(st.session_state.inbox_offset_stack) > 1:
        st.session_state.loading = True
        st.session_state.pending_action = "prev"
        st.session_state.pending_offset = st.session_state.inbox_offset_stack[-2]
        st.rerun()

# --------------------------------------------------------------------------
# Perform whichever pagination action was recorded above. Runs on the
# rerun AFTER the one that set loading=True, so the disabled-controls
# state has already been rendered at least once before this fetch
# starts.
# --------------------------------------------------------------------------
if st.session_state.loading and st.session_state.pending_action is not None:
    action = st.session_state.pending_action
    new_offset = st.session_state.pending_offset
    spinner_text = {
        "refresh": "Fetching inbox...",
        "next": "Loading next page...",
        "prev": "Loading previous page...",
    }[action]

    fetch_limit = MAX_EMAILS_FETCH
    if action == "refresh" and st.session_state.new_mail_count > MAX_EMAILS_FETCH:
        fetch_limit = st.session_state.new_mail_count

    with st.spinner(spinner_text):
        client = st.session_state.imap_client
        result = refresh_inbox_conversations(
            client, limit=fetch_limit, offset=new_offset, refresh=(action == "refresh"),
            store=st.session_state.email_store,
        )

    if result["success"]:
        new_conversations = result.get("conversations", [])

        if action == "refresh":
            st.session_state.inbox_offset_stack = [0]
            st.session_state.inbox_conv_offset_stack = [0]
            st.session_state.inbox_conv_ratio_raw_sum = len(result["emails"])
            st.session_state.inbox_conv_ratio_conv_sum = len(new_conversations)
        elif action == "next":
            st.session_state.inbox_offset_stack.append(new_offset)
            st.session_state.inbox_conv_offset_stack.append(
                st.session_state.inbox_conv_offset_stack[-1] + len(st.session_state.conversations)
            )
            st.session_state.inbox_conv_ratio_raw_sum += len(result["emails"])
            st.session_state.inbox_conv_ratio_conv_sum += len(new_conversations)
        elif action == "prev" and len(st.session_state.inbox_offset_stack) > 1:
            st.session_state.inbox_offset_stack.pop()
            st.session_state.inbox_conv_offset_stack.pop()

        st.session_state.emails = result["emails"]
        st.session_state.conversations = new_conversations
        st.session_state.inbox_total = result["total"]
        st.session_state.inbox_offset = new_offset
        st.session_state.inbox_has_more = result.get("has_more", False)
        st.session_state.inbox_raw_consumed = result.get("raw_consumed", len(result["emails"]))

        if action == "refresh":

            st.session_state.inbox_total_conversations = None
        # inbox_total is now current, so any pending new-mail banner is
        # stale — clear it immediately rather than waiting for the next
        # throttled check.
        st.session_state.new_mail_count = 0
        if "store_error" in result:
            print(f"[app] DB save failed on '{action}': {result['store_error']}", flush=True)
    else:
        st.error(f"Could not fetch inbox: {result['error']}")

    st.session_state.loading = False
    st.session_state.pending_action = None
    st.rerun()
