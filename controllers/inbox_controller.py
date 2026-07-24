import time

import streamlit as st

from config import MAX_EMAILS_FETCH
from services.email_service import (
    load_cached_inbox,
    refresh_inbox,
    search_inbox,
    sync_all_inbox,
)
from ui.styles import section_label


# Show the shared activity bar in the sidebar.
def start_sidebar_activity(activity_slot, text: str, value: float = 0.05):
    activity_slot.empty()
    with activity_slot.container():
        st.markdown(section_label("Activity"), unsafe_allow_html=True)
        return st.progress(value, text=text)


# Update the sidebar activity bar.
def update_sidebar_activity(progress, value: float, text: str):
    if progress is not None:
        progress.progress(max(0.0, min(value, 1.0)), text=text)


# Mark the sidebar activity as complete.
def finish_sidebar_activity(progress, text: str):
    update_sidebar_activity(progress, 1.0, text)


# Remove the sidebar activity area.
def clear_sidebar_activity(activity_slot):
    activity_slot.empty()


# Apply one saved database page to the current inbox state.
def _apply_cached_page(page: dict, offset: int):
    st.session_state.emails = page["emails"]
    st.session_state.inbox_total = page["total"]
    st.session_state.inbox_has_more = page.get("has_more", False)
    st.session_state.inbox_offset = offset


# Load one inbox page from SQLite.
def load_local_page(offset: int = 0, folder: str = "INBOX") -> bool:
    result = load_cached_inbox(
        st.session_state.email_store,
        limit=MAX_EMAILS_FETCH,
        offset=offset,
        folder=folder,
    )
    if not result["success"]:
        st.error(f"Could not load the local inbox: {result['error']}")
        return False
    _apply_cached_page(result, offset)
    return True


# Open the saved inbox or fetch the first page when it is empty.
def load_inbox_if_needed(activity_slot, folder: str = "INBOX"):
    if st.session_state.inbox_loaded:
        return

    inbox_progress = start_sidebar_activity(
        activity_slot, "Opening saved inbox...", 0.08
    )
    inbox_load_succeeded = True
    cached = load_cached_inbox(
        st.session_state.email_store,
        limit=MAX_EMAILS_FETCH,
        offset=0,
        folder=folder,
    )
    if not cached["success"]:
        clear_sidebar_activity(activity_slot)
        st.error(f"Could not open the local inbox: {cached['error']}")
        st.stop()

    update_sidebar_activity(
        inbox_progress, 0.32, "Checking mailbox status..."
    )
    remote_total = st.session_state.imap_client.get_message_count(folder)
    sync_state = st.session_state.email_store.get_sync_state(folder)

    if cached["total"] > 0:
        update_sidebar_activity(
            inbox_progress, 0.78, "Preparing saved inbox..."
        )
        _apply_cached_page(cached, 0)

        if sync_state and sync_state.get("full_sync_complete"):
            st.session_state.full_synced = True
        elif sync_state is None:
            # Treat an older database as a completed local cache.
            st.session_state.email_store.mark_sync_complete(
                folder, remote_total or cached["total"], cached["total"]
            )
            st.session_state.full_synced = True
    else:
        update_sidebar_activity(
            inbox_progress, 0.42, "Fetching the first inbox page..."
        )
        first_page = refresh_inbox(
            st.session_state.imap_client,
            limit=MAX_EMAILS_FETCH,
            offset=0,
            refresh=True,
            store=st.session_state.email_store,
            folder=folder,
            sync_source="initial_page",
        )
        if first_page["success"]:
            update_sidebar_activity(
                inbox_progress, 0.86, "Loading the saved inbox page..."
            )
            load_local_page(0, folder)
        else:
            inbox_load_succeeded = False
            st.error(f"Could not fetch inbox: {first_page['error']}")

    st.session_state.inbox_loaded = True
    if inbox_load_succeeded:
        finish_sidebar_activity(inbox_progress, "Inbox ready")
    clear_sidebar_activity(activity_slot)


# Run the full mailbox sync only when it has never completed.
def run_full_sync_if_needed(activity_slot, folder: str = "INBOX"):
    if not (
        st.session_state.inbox_loaded
        and not st.session_state.full_synced
        and not st.session_state.full_sync_attempted
    ):
        return

    st.session_state.full_sync_attempted = True
    sync_progress = start_sidebar_activity(
        activity_slot, "Syncing all emails for first-time setup...", 0.0
    )

    # Update the first-time sync progress after each saved batch.
    def _update_sync_progress(synced, total):
        fraction = min(synced / total, 1.0) if total else 0.0
        update_sidebar_activity(
            sync_progress,
            fraction,
            f"First-time sync: {synced:,} / {total or '?'}",
        )

    sync_result = sync_all_inbox(
        st.session_state.imap_client,
        st.session_state.email_store,
        folder=folder,
        progress_callback=_update_sync_progress,
    )
    if sync_result["success"]:
        finish_sidebar_activity(sync_progress, "First-time sync complete")
        st.session_state.full_synced = True
        load_local_page(0, folder)
    else:
        st.warning(
            "The first-time full sync did not finish. Cached emails remain usable, "
            "and the app will try again after a future login or server restart."
        )
        print(
            f"[app] Full sync stopped after {sync_result['synced']} email(s): "
            f"{sync_result['error']}",
            flush=True,
        )
    clear_sidebar_activity(activity_slot)


# Check the remote count without downloading the mailbox.
def check_new_messages(folder: str = "INBOX", check_seconds: int = 30):
    if (
        st.session_state.inbox_loaded
        and not st.session_state.loading
        and (time.time() - st.session_state.last_mail_check) > check_seconds
    ):
        st.session_state.last_mail_check = time.time()
        current_count = st.session_state.imap_client.get_message_count(folder)
        local_count = st.session_state.email_store.get_count(folder)
        if current_count is not None:
            st.session_state.email_store.update_remote_total(folder, current_count)
            st.session_state.new_mail_count = max(current_count - local_count, 0)


# Show a notice when new remote messages are available.
def render_new_mail_notice():
    if st.session_state.new_mail_count > 0:
        st.info(
            f"📥 {st.session_state.new_mail_count} new message"
            f"{'s' if st.session_state.new_mail_count != 1 else ''} — "
            "click the refresh icon to load them."
        )


# Process search, refresh, and pagination actions.
def handle_inbox_actions(inbox_actions, activity_slot, folder: str = "INBOX"):
    query = (inbox_actions["query"] or "").strip()
    if inbox_actions["search"] and query:
        search_progress = start_sidebar_activity(
            activity_slot, "Searching saved mail...", 0.12
        )
        result = search_inbox(st.session_state.email_store, query, folder=folder)
        update_sidebar_activity(
            search_progress, 0.82, "Preparing search results..."
        )
        if result["success"]:
            st.session_state.search_results = result["emails"]
            st.session_state.search_total = result["total"]
            st.session_state.search_active = True
            st.session_state.selected_uid = None
            finish_sidebar_activity(search_progress, "Search complete")
        else:
            st.error(f"Search failed: {result['error']}")
        clear_sidebar_activity(activity_slot)
        st.rerun()

    if inbox_actions["clear_search"]:
        st.session_state.search_active = False
        st.session_state.search_results = []
        st.session_state.search_total = 0
        st.session_state.selected_uid = None
        st.rerun()

    if inbox_actions["refresh"] and not st.session_state.loading:
        st.session_state.loading = True
        refresh_progress = start_sidebar_activity(
            activity_slot, "Checking for new emails...", 0.08
        )
        fetch_limit = max(MAX_EMAILS_FETCH, st.session_state.new_mail_count)
        update_sidebar_activity(
            refresh_progress, 0.30, "Fetching and updating the local inbox..."
        )
        result = refresh_inbox(
            st.session_state.imap_client,
            limit=fetch_limit,
            offset=0,
            refresh=True,
            store=st.session_state.email_store,
            folder=folder,
            sync_source="manual_refresh",
        )

        if result["success"]:
            update_sidebar_activity(
                refresh_progress, 0.84, "Reloading the inbox..."
            )
            st.session_state.email_store.update_remote_total(folder, result["total"])
            load_local_page(0, folder)
            st.session_state.search_active = False
            st.session_state.search_results = []
            st.session_state.search_total = 0
            st.session_state.selected_uid = None
            st.session_state.new_mail_count = 0
            finish_sidebar_activity(refresh_progress, "Inbox refreshed")
        else:
            st.error(f"Could not refresh inbox: {result['error']}")
        st.session_state.loading = False
        clear_sidebar_activity(activity_slot)
        st.rerun()

    if inbox_actions["next"]:
        page_progress = start_sidebar_activity(
            activity_slot, "Loading the next inbox page...", 0.24
        )
        next_offset = st.session_state.inbox_offset + MAX_EMAILS_FETCH
        if load_local_page(next_offset, folder):
            st.session_state.selected_uid = None
            finish_sidebar_activity(page_progress, "Next page ready")
        clear_sidebar_activity(activity_slot)
        st.rerun()

    if inbox_actions["prev"]:
        page_progress = start_sidebar_activity(
            activity_slot, "Loading the previous inbox page...", 0.24
        )
        previous_offset = max(0, st.session_state.inbox_offset - MAX_EMAILS_FETCH)
        if load_local_page(previous_offset, folder):
            st.session_state.selected_uid = None
            finish_sidebar_activity(page_progress, "Previous page ready")
        clear_sidebar_activity(activity_slot)
        st.rerun()
