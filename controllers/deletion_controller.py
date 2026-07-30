"""Apply confirmed external mailbox deletions to Streamlit UI state."""

import streamlit as st

from services.deletion_detection_service import reconcile_folder


def build_deletion_notice(count: int) -> str:
    noun = "email" if count == 1 else "emails"
    return (
        f"{count} {noun} no longer exists in this mailbox folder and "
        f"{'was' if count == 1 else 'were'} removed from the inbox view."
    )


def clear_unavailable_email_state(unavailable_uids) -> int:
    """Remove confirmed missing UIDs from all live inbox-related UI state."""
    unavailable = {str(uid) for uid in unavailable_uids if str(uid)}
    if not unavailable:
        return 0

    st.session_state.checked_uids = set(
        st.session_state.get("checked_uids", set())
    ).difference(unavailable)
    st.session_state.new_email_uids = set(
        st.session_state.get("new_email_uids", set())
    ).difference(unavailable)

    if str(st.session_state.get("selected_uid")) in unavailable:
        st.session_state.selected_uid = None

    st.session_state.emails = [
        email
        for email in st.session_state.get("emails", [])
        if str(email.get("uid")) not in unavailable
    ]
    st.session_state.inbox_total = max(
        0,
        int(st.session_state.get("inbox_total", 0)) - len(unavailable),
    )
    old_results = st.session_state.get("search_results", [])
    st.session_state.search_results = [
        email
        for email in old_results
        if str(email.get("uid")) not in unavailable
    ]
    st.session_state.search_total = max(
        0,
        int(st.session_state.get("search_total", 0))
        - (len(old_results) - len(st.session_state.search_results)),
    )

    bodies = st.session_state.get("email_bodies", {})
    for cache_key in list(bodies):
        try:
            cached_uid = str(cache_key[2])
        except (IndexError, TypeError):
            continue
        if cached_uid in unavailable:
            bodies.pop(cache_key, None)

    for uid in unavailable:
        st.session_state.pop(f"chk_{uid}", None)
    return len(unavailable)


def apply_confirmed_deletions(unavailable_uids) -> int:
    """Update live state and prepare one user-facing notice."""
    removed = clear_unavailable_email_state(unavailable_uids)
    if removed:
        st.session_state.email_deletion_notice = build_deletion_notice(removed)
    return removed


def reconcile_mailbox_state(client, store, folder: str = "INBOX"):
    """Run the service-layer comparison and apply confirmed deletions."""
    result = reconcile_folder(client, store, folder)
    if result.success:
        apply_confirmed_deletions(result.missing_uids)
    return result
