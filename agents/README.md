# Agents layer

Each specialist agent is built with LangChain and LangGraph, then packaged
using the MLflow Models-as-Code pattern so that it can be registered and
served by the Mosaic AI Agent Framework on a Databricks Model Serving
endpoint. Solace Agent Mesh then talks to these endpoints, not to this code
directly.

| File | Role |
|---|---|
| `trend_agent.py` | Trend synthesis and material recommendation |
| `sustainability_agent.py` | Material and circularity analysis |
| `storytelling_agent.py` | Narrative and positioning generation |
| `buyer_agent.py` | Demand, feasibility and inventory commentary |
| `register_mosaic_agents.py` | Packages and registers all four agents with Mosaic AI |
| `hitl_orchestrator.py` | LangGraph state machine driving the Designer to Buyer to Sustainability to Marketing approval flow |

`hitl_orchestrator.py` is the only piece of agent logic that is not served
through Mosaic AI: it is the workflow controller the Streamlit app talks to
directly, since it owns conversation state and the Human-in-the-Loop
checkpoints rather than a single specialist task.
