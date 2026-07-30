"""Background-safe coordination for AI summary generation and reading."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import streamlit as st

from services.email_service import get_full_email
from services.summary_service import create_summary


class SummaryProgress:
    """Thread-safe, UI-readable progress snapshot for one summary job."""

    def __init__(self, total: int):
        self.total = total
        self.processed = 0
        self._lock = Lock()

    def advance(self):
        with self._lock:
            self.processed += 1

    def snapshot(self):
        with self._lock:
            return self.processed, self.total


def _summarize_batch(client, email_store, headers: list[dict], folder: str,
                     progress: SummaryProgress) -> dict:
    """Run outside Streamlit's UI thread so navigation cannot cancel the work."""
    summaries, failures = [], []
    for header in headers:
        uid = str(header["uid"])
        result = get_full_email(client, uid, folder=folder, store=email_store)
        if not result["success"]:
            failures.append((header.get("subject") or uid, result["error"]))
            progress.advance()
            continue
        try:
            summaries.append(create_summary(result["email"]))
        except RuntimeError as error:
            failures.append((header.get("subject") or uid, str(error)))
        progress.advance()
    return {"summaries": summaries, "failures": failures}


def _selected_headers(list_source, folder: str) -> list[dict]:
    """Resolve all checked UIDs from storage, including selections on other pages."""
    selected_uids = set(st.session_state.checked_uids)
    fallback = {str(item.get("uid")): item for item in list_source}
    headers = []
    for uid in selected_uids:
        header = st.session_state.email_store.get_email(folder, uid)
        if header is not None:
            headers.append(header)
        elif uid in fallback:
            headers.append(fallback[uid])
    return headers


def start_summary_generation(list_source, folder: str = "INBOX") -> bool:
    """Start a single background job for every checked, unsummarized message."""
    if st.session_state.summary_processing:
        return False

    selected_uids = set(st.session_state.checked_uids)
    headers = _selected_headers(list_source, folder)
    if not headers:
        return False

    saved_uids = st.session_state.summary_store.get_uids(folder)
    pending_headers = [
        header for header in headers if str(header.get("uid")) not in saved_uids
    ]
    skipped = len(headers) - len(pending_headers)
    if skipped:
        st.info(
            f"{skipped} selected email{' is' if skipped == 1 else 's are'} already "
            "summarized and will not be added again."
        )
    if not pending_headers:
        return False

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="email-summary")
    progress = SummaryProgress(len(pending_headers))
    st.session_state.summary_executor = executor
    st.session_state.summary_future = executor.submit(
        _summarize_batch,
        st.session_state.imap_client,
        st.session_state.email_store,
        pending_headers,
        folder,
        progress,
    )
    st.session_state.summary_progress = progress
    st.session_state.summary_job_uids = list(selected_uids)
    st.session_state.summary_processing = True
    return True


def render_summary_activity(activity_slot):
    """Render the shared sidebar activity bar for an active background job."""
    if not st.session_state.get("summary_processing"):
        return
    progress = st.session_state.get("summary_progress")
    if progress is None:
        return
    processed, total = progress.snapshot()
    fraction = processed / total if total else 0.0
    activity_slot.empty()
    with activity_slot.container():
        st.markdown('<div class="section-label">Activity</div>', unsafe_allow_html=True)
        st.progress(
            min(fraction, 1.0),
            text=f"Summarizing emails: {processed} of {total}",
        )


@st.fragment(run_every=1.0)
def monitor_summary_generation(activity_slot, folder: str = "INBOX"):
    """Refresh only the activity area while a background job is running.

    ``st.autorefresh`` is intentionally not used: it is not part of Streamlit's
    public API in every supported version.  A fragment is Streamlit's supported
    way to run a small, periodic UI update without re-running the inbox or
    cancelling the worker thread.
    """
    if not st.session_state.get("summary_processing"):
        return

    if poll_summary_generation(folder=folder):
        activity_slot.empty()
        # The completed job changed summaries and the active workspace.  Re-run
        # the full app once so those changes are rendered immediately.
        st.rerun(scope="app")

    render_summary_activity(activity_slot)


def poll_summary_generation(folder: str = "INBOX") -> bool:
    """Commit a completed background job on the UI thread and report completion."""
    future = st.session_state.get("summary_future")
    if not st.session_state.get("summary_processing") or future is None:
        return False
    if not future.done():
        return False

    st.session_state.summary_processing = False
    try:
        result = future.result()
    except Exception as error:
        st.error(f"Summary generation stopped: {error}")
        return True
    finally:
        executor = st.session_state.pop("summary_executor", None)
        if executor is not None:
            executor.shutdown(wait=False)
        st.session_state.pop("summary_future", None)
        st.session_state.pop("summary_progress", None)

    summaries = result["summaries"]
    if summaries:
        st.session_state.summary_store.append_all(folder, summaries)
        st.session_state.summaries = st.session_state.summary_store.load_all(folder)
        st.session_state.selected_summary_uid = st.session_state.summaries[0]["uid"]
        st.session_state.clear_checked_after_summary = st.session_state.pop(
            "summary_job_uids", []
        )
        st.session_state.switch_to_summary = True
        st.success(f"Generated {len(summaries)} AI summar{'y' if len(summaries) == 1 else 'ies'}.")
    else:
        st.session_state.pop("summary_job_uids", None)

    for subject, error in result["failures"]:
        st.warning(f"Could not summarize '{subject}': {error}")
    return True


def open_summary(uid: str, folder: str = "INBOX"):
    """Select a summary and persist its read status."""
    st.session_state.summary_store.mark_read(folder, uid)
    st.session_state.summaries = st.session_state.summary_store.load_all(folder)
    st.session_state.selected_summary_uid = str(uid)
