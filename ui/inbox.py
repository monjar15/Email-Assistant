import streamlit as st

from ui.styles import section_label

LIST_HEIGHT = 560  # px — fixed height; Streamlit adds a scrollbar past this


def _as_conversations(emails):
    # Fallback used when the caller hasn't passed `conversations`.
    return [
        {
            "thread_id": e.get("uid", ""),
            "subject": e.get("subject") or "(No Subject)",
            "emails": [e],
            "all_uids": [e["uid"]] if e.get("uid") else [],
            "count": 1,
            "latest_date": e.get("date", ""),
            "latest_date_display": e.get("date_display", "Unknown"),
            "participants": [p for p in (e.get("from"),) if p],
            "is_thread": False,
            "all_mail_folder": None,
        }
        for e in emails
    ]


def render_inbox(emails, total: int = 0, offset: int = 0, limit: int = 50,
                  loading: bool = False, checked_uids=None,
                  search_active: bool = False, conversations=None,
                  can_prev: bool = None, can_next: bool = None,
                  conv_offset: int = 0, total_conversations: int = None,
                  total_conversations_is_estimate: bool = True) -> dict:

    if checked_uids is None:
        checked_uids = set()

    conversations = conversations if conversations is not None else _as_conversations(emails)

    # Row 1: section label + refresh icon (only 2 columns — plenty of room)
    col_label, col_refresh = st.columns([0.85, 0.15])
    with col_label:
        st.markdown(section_label("Inbox"), unsafe_allow_html=True)
    with col_refresh:
        refresh_clicked = st.button(
            "\u21bb", key="refresh_inbox_icon", help="Refresh inbox",
            use_container_width=True, disabled=loading,
        )

    # Row 2: search box + search button. Submitting via Enter (the text
    # input's own on_change) or clicking the button both count as "search".
    col_query, col_search_btn = st.columns([0.87, 0.13], gap="small")
    with col_query:
        query = st.text_input(
            "Search", key="inbox_search_query", placeholder="Search subject or sender\u2026",
            label_visibility="collapsed", disabled=loading,
        )
    with col_search_btn:
        search_clicked = st.button(
            "\U0001F50D", key="inbox_search_btn", help="Search",
            use_container_width=True, disabled=loading,
        )

    # Row 3: page range + prev/next while browsing normally, or a "back
    # to inbox" link while showing search results (which aren't paginated).
    clear_search_clicked = False
    if search_active:
        col_range, col_clear = st.columns([0.68, 0.32], gap="small")
        with col_range:
            st.markdown(
                f'<div class="item-meta" style="padding-top: 0.5rem; white-space: nowrap;">'
                f'{len(conversations)} result{"s" if len(conversations) != 1 else ""}</div>',
                unsafe_allow_html=True,
            )
        with col_clear:
            clear_search_clicked = st.button(
                "\u2190 Back to inbox", key="inbox_clear_search",
                use_container_width=True, disabled=loading,
            )
        prev_clicked = False
        next_clicked = False
    else:
        start = conv_offset + 1 if total > 0 and conversations else 0
        end = conv_offset + len(conversations)

        display_total = total_conversations if total_conversations is not None else total
        tilde = "~" if total_conversations_is_estimate else ""

        col_range, col_prev, col_next = st.columns([0.68, 0.16, 0.16], gap="small")
        with col_range:
            st.markdown(
                f'<div class="item-meta" style="padding-top: 0.5rem; white-space: nowrap;">'
                f'{start}\u2013{end} of {tilde}{display_total:,}</div>',
                unsafe_allow_html=True,
            )
        prev_allowed = can_prev if can_prev is not None else (offset > 0)
        next_allowed = can_next if can_next is not None else (offset + limit < total)

        with col_prev:
            prev_clicked = st.button(
                "\u2039", key="inbox_prev_page", help="Previous page",
                use_container_width=True, disabled=(loading or not prev_allowed),
            )
        with col_next:
            next_clicked = st.button(
                "\u203a", key="inbox_next_page", help="Next page",
                use_container_width=True, disabled=(loading or not next_allowed),
            )

    actions = {
        "refresh": refresh_clicked,
        "prev": prev_clicked,
        "next": next_clicked,
        "search": search_clicked,
        "clear_search": clear_search_clicked,
        "query": query,
        "checked_uids": set(checked_uids),
    }

    if not emails:
        empty_msg = "No emails match that search." if search_active else \
            "No emails fetched yet. Click the refresh icon above."
        st.markdown(f'<div class="empty-state">{empty_msg}</div>', unsafe_allow_html=True)
        return actions

    new_checked = set()
    with st.container(height=LIST_HEIGHT, border=False):
        for conv in conversations:
            thread_uids = conv.get("all_uids") or [m["uid"] for m in conv["emails"]]
            latest = conv["emails"][0]
            is_selected = (
                st.session_state.get("selected_thread_id") == conv["thread_id"]
                or st.session_state.get("selected_uid") in thread_uids
            )

            conv_checked = bool(thread_uids) and all(u in checked_uids for u in thread_uids)

            # Side checkbox (Gmail-style multi-select) + subject row.
            col_check, col_row = st.columns([0.12, 0.88], gap="small")
            with col_check:
                checked = st.checkbox(
                    "Select", key=f"chk_{conv['thread_id']}", value=conv_checked,
                    disabled=loading, label_visibility="collapsed",
                )
                if checked:
                    new_checked.update(thread_uids)
            with col_row:
                subject = conv["subject"] or "(No Subject)"
                badge = f"  ({conv['count']})" if conv["is_thread"] else ""
                from_label = latest.get("from", "")
                clicked = st.button(
                    f"{subject}{badge}  \n{from_label}",
                    key=f"conv_{conv['thread_id']}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                    disabled=loading,
                )
                if clicked:
                    st.session_state.selected_uid = latest["uid"]
                    st.session_state.selected_thread_id = conv["thread_id"]
                    st.rerun()

    actions["checked_uids"] = new_checked
    return actions