# Streamlit front end

The conversational entry point for every persona. Talks to
`agents/hitl_orchestrator.py` for workflow state and decisions, and to the
Solace Agent Mesh REST gateway for the actual specialist agent calls that
orchestrator triggers at each stage.

Run locally with `streamlit run app.py` from this folder, with the project
root's `.env` already populated.
