import streamlit as st

from controllers.inbox_controller import (
    clear_sidebar_activity,
    finish_sidebar_activity,
    start_sidebar_activity,
    update_sidebar_activity,
)
from services.email_service import get_full_email


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
            else:
                st.error(f"Could not load email: {body_result['error']}")
            clear_sidebar_activity(activity_slot)
        selected_message = st.session_state.email_bodies.get(cache_key)

    return selected_message
