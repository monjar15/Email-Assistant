"""AI Summary workspace laid out like the Inbox workspace."""
import streamlit as st

from controllers.summary_controller import open_summary
from ui.summary_list import render_summary_list
from ui.summary_reader import render_summary_reader


def render_summary_tab():
    summaries = st.session_state.summaries
    with st.container(border=False, key="summary_workspace"):
        col_list, col_content = st.columns([0.4, 0.6], gap="large")
        with col_list:
            with st.container(key="summary_outer_pane"):
                st.markdown('<div class="pane-heading">AI Summary</div>', unsafe_allow_html=True)
                opened_uid = render_summary_list(summaries)
                if opened_uid is not None:
                    open_summary(opened_uid)
                    st.rerun()
        with col_content:
            with st.container(key="summary_content_outer_pane"):
                st.markdown(
                    '<div class="pane-heading pane-heading-right">Summary Content</div>',
                    unsafe_allow_html=True,
                )
                selected = next(
                    (item for item in summaries if str(item["uid"]) == str(
                        st.session_state.selected_summary_uid
                    )),
                    None,
                )
                render_summary_reader(selected)
