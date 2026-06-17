"""
ATELIER conversational demo: a minimal Streamlit front end over the HITL
orchestrator. This is intentionally thin; the workflow logic itself lives
in agents/hitl_orchestrator.py, not here.
"""

import os
import sys
import uuid

import streamlit as st
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agents"))
from hitl_orchestrator import build_graph, submit_decision  # noqa: E402

load_dotenv()

st.set_page_config(page_title="ATELIER", layout="centered")
st.title("ATELIER")
st.caption("Conversational AI platform for the fashion industry, demo pilot")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

with st.form("brief_form"):
    brief = st.text_area("Describe the collection brief", height=120)
    submitted = st.form_submit_button("Start concept")

if submitted and brief:
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    st.session_state.graph.invoke(
        {
            "collection_id": st.session_state.thread_id,
            "brief": brief,
            "trend_proposal": "",
            "buyer_commentary": "",
            "sustainability_assessment": "",
            "narrative": "",
            "stage": "",
            "last_decision": {},
        },
        config,
    )
    st.success("Concept submitted. Awaiting the next Human-in-the-Loop decision.")

st.divider()
st.subheader("Human-in-the-Loop decision")
decision_type = st.selectbox("Decision", ["approve", "modify", "escalate"])
comment = st.text_input("Comment")

if st.button("Submit decision"):
    submit_decision(
        st.session_state.graph,
        st.session_state.thread_id,
        {"decision_type": decision_type, "comment": comment},
    )
    st.success("Decision recorded, workflow resumed.")
