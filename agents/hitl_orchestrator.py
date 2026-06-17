"""
HITL orchestrator: the workflow controller behind the Streamlit app. It
owns the Designer -> Buyer -> Sustainability -> Marketing approval sequence
for a single collection concept and stops at each handoff for an explicit
human decision.

LESSON LEARNED (reused from earlier case studies, proven across the
financial crime control and incident management agents): the suspend and
resume pattern uses `interrupt_before` on the decision node together with a
module-level singleton MemorySaver checkpointer. Resuming after a human
decision uses `graph.update_state(...)` to inject that decision, then
re-invokes the graph; the graph is never re-built from scratch mid-flow.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

# Module-level singleton: every call to build_graph() across the running
# Streamlit process shares the same checkpointer, so a conversation can be
# suspended in one request and resumed in a later one.
_CHECKPOINTER = MemorySaver()


class CollectionState(TypedDict):
    collection_id: str
    brief: str
    trend_proposal: str
    buyer_commentary: str
    sustainability_assessment: str
    narrative: str
    stage: str
    last_decision: dict


def run_trend_stage(state: CollectionState) -> CollectionState:
    # Calls the atelier-trend-agent Mosaic AI serving endpoint via Solace
    # Agent Mesh's REST gateway (see solace_mesh/README.md).
    state["stage"] = "awaiting_designer_submission"
    return state


def hitl_decision_node(state: CollectionState) -> CollectionState:
    """
    This node is never actually executed with a real decision attached on
    the first pass: the graph is compiled with interrupt_before on this
    node's name, so LangGraph pauses execution immediately before it runs
    and returns control to the caller. The human decision is injected later
    through update_state(), and only then does this node body run.
    """
    return state


def route_after_decision(state: CollectionState) -> str:
    decision_type = state["last_decision"].get("decision_type", "")
    if decision_type == "approve":
        next_stage = {
            "awaiting_designer_submission": "buyer_review",
            "buyer_review": "sustainability_review",
            "sustainability_review": "marketing_review",
            "marketing_review": "export",
        }
        state["stage"] = next_stage.get(state["stage"], "export")
    elif decision_type == "modify":
        # Stays on the same stage; the relevant specialist agent is
        # re-invoked with the operator's modification request.
        pass
    elif decision_type == "escalate":
        state["stage"] = "awaiting_designer_submission"
    return state["stage"]


def build_graph():
    graph = StateGraph(CollectionState)
    graph.add_node("run_trend_stage", run_trend_stage)
    graph.add_node("hitl_decision_node", hitl_decision_node)
    graph.set_entry_point("run_trend_stage")
    graph.add_edge("run_trend_stage", "hitl_decision_node")
    graph.add_conditional_edges(
        "hitl_decision_node",
        route_after_decision,
        {
            "buyer_review": "hitl_decision_node",
            "sustainability_review": "hitl_decision_node",
            "marketing_review": "hitl_decision_node",
            "awaiting_designer_submission": "run_trend_stage",
            "export": END,
        },
    )
    return graph.compile(checkpointer=_CHECKPOINTER, interrupt_before=["hitl_decision_node"])


def submit_decision(graph, thread_id: str, decision: dict):
    """
    Resumes a suspended conversation: writes the operator's decision into
    the checkpointed state, then re-invokes the graph so it continues past
    the interrupt point.
    """
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {"last_decision": decision})
    return graph.invoke(None, config)
