"""
Inbox list UI: displays the emails currently held in session state
(populated by the "Refresh Inbox" fetch in app.py) inside a fixed-height,
scrollable panel. Clicking an email selects it directly — there is no
separate "Open" step; the row itself is the click target, and the
selected row is highlighted.

No persistence here — fetched emails live only in st.session_state for
the current session, since there is no database in this phase.
"""
import streamlit as st

from ui.styles import section_label

LIST_HEIGHT = 560  # px — fixed height; Streamlit adds a scrollbar past this


def render_inbox(emails, total: int = 0, offset: int = 0, limit: int = 50,
                  loading: bool = False, checked_uids=None,
                  search_active: bool = False) -> dict:

    if checked_uids is None:
        checked_uids = set()

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
                f'{len(emails)} result{"s" if len(emails) != 1 else ""}</div>',
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
        start = offset + 1 if total > 0 and emails else 0
        end = offset + len(emails)

        col_range, col_prev, col_next = st.columns([0.68, 0.16, 0.16], gap="small")
        with col_range:
            st.markdown(
                f'<div class="item-meta" style="padding-top: 0.5rem; white-space: nowrap;">'
                f'{start}\u2013{end} of {total:,}</div>',
                unsafe_allow_html=True,
            )
        with col_prev:
            prev_clicked = st.button(
                "\u2039", key="inbox_prev_page", help="Previous page",
                use_container_width=True, disabled=(loading or offset <= 0),
            )
        with col_next:
            next_clicked = st.button(
                "\u203a", key="inbox_next_page", help="Next page",
                use_container_width=True, disabled=(loading or offset + limit >= total),
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
        for e in emails:
            is_selected = st.session_state.get("selected_uid") == e["uid"]

            # Side checkbox (Gmail-style multi-select) + subject-only row.
            col_check, col_row = st.columns([0.12, 0.88], gap="small")
            with col_check:
                checked = st.checkbox(
                    "Select", key=f"chk_{e['uid']}", value=e["uid"] in checked_uids,
                    disabled=loading, label_visibility="collapsed",
                )
                if checked:
                    new_checked.add(e["uid"])
            with col_row:
                clicked = st.button(
                    f"{e['subject'] or '(No Subject)'}  \n{e['from']}",
                    key=f"email_{e['uid']}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                    disabled=loading,
                )
                if clicked:
                    st.session_state.selected_uid = e["uid"]
                    st.rerun()

    actions["checked_uids"] = new_checked
    return actions