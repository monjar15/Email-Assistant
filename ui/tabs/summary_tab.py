"""AI Summary workspace with filtering and persistent read state."""
import streamlit as st

from controllers.summary_controller import open_summary
from ui.summary_list import render_summary_list
from ui.summary_reader import render_summary_reader


def render_summary_tab():
    summaries = st.session_state.summaries
    with st.container(height=700, border=False, key="summary_workspace"):
        col_list, col_content = st.columns([0.4, 0.6], gap="large")
        with col_list:
            opened_uid = render_summary_list(summaries)
            if opened_uid is not None:
                open_summary(opened_uid)
                st.rerun()
        with col_content:
            selected = next(
                (item for item in summaries if str(item["uid"]) == str(
                    st.session_state.selected_summary_uid
                )),
                None,
            )
            render_summary_reader(selected)
