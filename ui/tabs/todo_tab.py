"""Todo List placeholder with a live count of task-ready summaries."""
import streamlit as st

from ui.summary_metrics import todo_task_count


def render_todo_tab():
    task_count = todo_task_count(st.session_state.get("summaries", []))
    task_label = "task-ready summary" if task_count == 1 else "task-ready summaries"
    with st.container(border=False, key="todo_workspace"):
        st.markdown(
            (
                f'<div class="todo-empty-shell">'
                f'<strong>{task_count:,}</strong> {task_label}<br>'
                '<span>Counted only from summaries that contain real action items. '
                'Automatic task creation will be added in the next feature.</span>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )
