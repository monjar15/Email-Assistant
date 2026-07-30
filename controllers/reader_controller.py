import time

import streamlit as st

from controllers.deletion_controller import apply_confirmed_deletions
from controllers.inbox_controller import (
    clear_sidebar_activity,
    finish_sidebar_activity,
    start_sidebar_activity,
    update_sidebar_activity,
)
from services.email_service import get_full_email
from services.deletion_detection_service import check_uid_availability


VALIDATION_TTL_SECONDS = 15


def _validation_cache_key(folder: str, uid: str):
    return (st.session_state.active_store_account, folder, str(uid))


def _validate_selected_uid(uid: str, folder: str) -> dict:
    cache_key = _validation_cache_key(folder, uid)
    cache = st.session_state.get("email_validation_cache", {})
    cached = cache.get(cache_key)
    now = time.time()
    if cached and now - cached.get("checked_at", 0) < VALIDATION_TTL_SECONDS:
        return cached

    result = check_uid_availability(
        st.session_state.imap_client,
        uid,
        folder=folder,
    )
    if result.get("success"):
        cache[cache_key] = {**result, "checked_at": now}
        st.session_state.email_validation_cache = cache
    return result


def _handle_confirmed_missing(uid: str, folder: str):
    st.session_state.email_store.mark_remote_unavailable(folder, [uid])
    apply_confirmed_deletions([uid])
    st.rerun()


# Load the selected email from SQLite or IMAP when needed.
def load_selected_message(list_source, activity_slot, folder: str = "INBOX"):
    selected_header = next(
        (
            email_item
            for email_item in list_source
            if str(email_item.get("uid")) == str(st.session_state.selected_uid)
        ),
        None,
    )
    selected_message = None
    if selected_header:
        uid = str(selected_header["uid"])
        validation = _validate_selected_uid(uid, folder)
        if validation.get("success") and not validation.get("available"):
            _handle_confirmed_missing(uid, folder)

        cache_key = (st.session_state.active_store_account, folder, uid)
        if cache_key not in st.session_state.email_bodies:
            preview_progress = start_sidebar_activity(
                activity_slot, "Opening email preview...", 0.10
            )
            update_sidebar_activity(
                preview_progress, 0.34, "Checking the saved email body..."
            )
            body_result = get_full_email(
                st.session_state.imap_client,
                uid,
                folder=folder,
                store=st.session_state.email_store,
            )
            update_sidebar_activity(
                preview_progress, 0.84, "Preparing email preview..."
            )
            if body_result["success"]:
                full_email = body_result["email"]
                attachments = full_email.pop("attachments", None)
                if attachments is None:
                    attachments = st.session_state.email_store.get_attachments(
                        folder, uid
                    )
                st.session_state.email_bodies[cache_key] = {
                    "email": full_email,
                    "attachments": attachments or [],
                }
                if "store_error" in body_result:
                    print(
                        f"[app] DB save failed on message open: "
                        f"{body_result['store_error']}",
                        flush=True,
                    )
                finish_sidebar_activity(preview_progress, "Email ready")
            elif body_result.get("missing"):
                clear_sidebar_activity(activity_slot)
                _handle_confirmed_missing(uid, folder)
            else:
                st.error(f"Could not load email: {body_result['error']}")
            clear_sidebar_activity(activity_slot)
        selected_message = st.session_state.email_bodies.get(cache_key)

    return selected_message
