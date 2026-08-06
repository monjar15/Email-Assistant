"""Reader UI for one structured AI email summary."""
import html
import streamlit as st
from ui.reader import _sender_avatar


EMPTY_MARKERS = {"", "none identified.", "none", "n/a", "na"}


def _clean_text(value, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _clean_list(values) -> list[str]:
    cleaned = []
    for value in values or []:
        text = str(value or "").strip()
        if not text or text.casefold() in EMPTY_MARKERS:
            continue
        cleaned.append(text)
    return cleaned


def _priority_badge(priority: str, extra_class: str = "") -> str:
    text = _clean_text(priority, "Medium")
    key = text.casefold()
    if key == "high":
        variant = "priority-high"
    elif key == "low":
        variant = "priority-low"
    else:
        variant = "priority-medium"
    extra = f" {extra_class}" if extra_class else ""
    return (
        f'<span class="summary-priority-badge {variant}{extra}">'
        f'{html.escape(text)}</span>'
    )


def _status_badge(status: str) -> str:
    text = _clean_text(status, "Pending")
    key = text.casefold().replace("_", " ")
    if key in {"complete", "completed", "done"}:
        label, variant = "Complete", "status-complete"
    elif key in {"in progress", "in-progress", "ongoing"}:
        label, variant = "In Progress", "status-in-progress"
    else:
        label, variant = "Pending", "status-pending"
    return (
        '<span class="summary-status-control">'
        '<span class="summary-status-label">Status:</span>'
        f'<span class="summary-status-badge {variant}">{html.escape(label)}</span>'
        '</span>'
    )


def _list_html(items: list[str], variant: str = "check") -> str:
    icon = "✓" if variant == "check" else "→"
    icon_class = "is-check" if variant == "check" else "is-action"
    rows = "".join(
        f'<li><span class="summary-list-icon {icon_class}">{icon}</span>'
        f'<span>{html.escape(item)}</span></li>'
        for item in items
    )
    return f'<ul class="summary-clean-list">{rows}</ul>'


def _divider_html() -> str:
    return '<div class="summary-section-divider" aria-hidden="true"></div>'


def _render_header(summary, task_mode: bool):
    sender = _clean_text(summary.get("from"))
    recipient = _clean_text(summary.get("to"))
    subject = _clean_text(summary.get("subject"), "(No Subject)")
    date_display = _clean_text(summary.get("date_display"), "Unknown")
    priority = _clean_text(summary.get("priority"), "Medium")
    status = _clean_text(summary.get("status"), "Pending")

    initial, avatar_class = _sender_avatar(sender)
    if task_mode:
        badge_html = (
            '<div class="summary-header-task-badges">'
            f'{_status_badge(status)}'
            f'{_priority_badge(priority, "top-badge")}'
            '</div>'
        )
    else:
        badge_html = ""

    st.markdown(
        f'''
        <div class="summary-view-card summary-view-header compact-view">
            <div class="summary-view-header-row compact-row">
                <div class="summary-view-avatar reader-avatar {avatar_class}">{html.escape(initial)}</div>
                <div class="summary-view-title-stack">
                    <div class="summary-view-subject">{html.escape(subject)}</div>
                    <div class="summary-view-meta-line is-line-1">
                        <span class="summary-meta-pill"><span class="summary-meta-icon">✉</span> From {html.escape(sender or "Unknown sender")}</span>
                        <span class="summary-meta-separator">›</span>
                        <span class="summary-meta-pill">To {html.escape(recipient or "Unknown recipient")}</span>
                    </div>
                    <div class="summary-view-meta-line is-line-2">
                        <span class="summary-meta-pill"><span class="summary-meta-icon">◷</span> {html.escape(date_display)}</span>
                    </div>
                </div>
                <div class="summary-header-badge-slot">{badge_html}</div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_summary_reader(summary):
    if not summary:
        with st.container(height=820, border=False, key="summary_reader_scroll"):
            st.markdown(
                '<div class="empty-state">Select a summarized email to view its AI summary here.</div>',
                unsafe_allow_html=True,
            )
        return

    overview = _clean_text(
        summary.get("summary"), "No summary text is available for this email."
    )
    key_points = _clean_list(summary.get("key_points"))
    deadlines = _clean_list(summary.get("deadlines"))
    action_items = _clean_list(summary.get("action_items"))

    has_deadlines = bool(deadlines)
    has_actions = bool(action_items)
    task_mode = has_deadlines or has_actions

    with st.container(border=False, key="summary_reader_header"):
        _render_header(summary, task_mode)

    with st.container(height=720, border=False, key="summary_reader_scroll"):
        st.markdown(
            f'''
            <div class="summary-view-section compact-view-section section-summary-block">
                <div class="summary-view-section-head compact-head">
                    <span class="summary-view-section-icon section-blue">≡</span>
                    <span>Summary</span>
                </div>
                <div class="summary-overview-card compact-overview">
                    <div class="summary-overview-mark">❝</div>
                    <div class="summary-overview-text">{html.escape(overview)}</div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        if has_deadlines:
            st.markdown(_divider_html(), unsafe_allow_html=True)
            deadline_rows = "".join(
                f'<div class="summary-deadline-item">{html.escape(item)}</div>'
                for item in deadlines
            )
            st.markdown(
                f'''
                <div class="summary-view-section compact-view-section section-deadline-block">
                    <div class="summary-view-section-head compact-head no-bottom-gap">
                        <span class="summary-view-section-icon section-sky">⌑</span>
                        <span>Important Deadline</span>
                    </div>
                    <div class="summary-deadline-values standalone-deadlines">{deadline_rows}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

        if key_points:
            st.markdown(_divider_html(), unsafe_allow_html=True)
            st.markdown(
                f'''
                <div class="summary-view-section compact-view-section section-keypoints-block">
                    <div class="summary-view-section-head compact-head">
                        <span class="summary-view-section-icon section-green">✓</span>
                        <span>Key Points</span>
                    </div>
                    {_list_html(key_points, "check")}
                </div>
                ''',
                unsafe_allow_html=True,
            )

        if action_items:
            st.markdown(_divider_html(), unsafe_allow_html=True)
            st.markdown(
                f'''
                <div class="summary-view-section compact-view-section section-action-block">
                    <div class="summary-view-section-head compact-head">
                        <span class="summary-view-section-icon section-amber">→</span>
                        <span>Action Items</span>
                    </div>
                    {_list_html(action_items, "action")}
                </div>
                ''',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(_divider_html(), unsafe_allow_html=True)
            st.markdown(
                '''
                <div class="summary-no-action-card compact-no-action">
                    <div class="summary-no-action-icon">i</div>
                    <div class="summary-no-action-copy">
                        <div class="summary-no-action-title">No action required</div>
                        <div class="summary-no-action-text">This email is for your information only.</div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="summary-reader-bottom-spacer"></div>', unsafe_allow_html=True)
