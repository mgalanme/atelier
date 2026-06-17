"""
Trend synthesis agent: given a creative brief, retrieves relevant historical
and current trend signals via Mosaic AI Vector Search and proposes concept
directions and material recommendations.

Packaged with MLflow Models-as-Code: this module exposes a single `model`
object implementing `predict`, which is what Mosaic AI Agent Framework
expects when serving the agent as a Databricks Model Serving endpoint.
"""

import os

import mlflow
from langchain_community.chat_models import ChatDatabricks
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


class TrendState(TypedDict):
    brief: str
    retrieved_signals: list[str]
    proposal: str


def retrieve_signals(state: TrendState) -> TrendState:
    # Replace with a real call to the atelier-vector-search index created
    # in databricks/05_vector_search_setup.py.
    state["retrieved_signals"] = []
    return state


def synthesise_proposal(state: TrendState) -> TrendState:
    llm = ChatDatabricks(endpoint=os.environ["MOSAIC_LLM_ENDPOINT"])
    context = "\n".join(state["retrieved_signals"]) or "No prior signals retrieved."
    prompt = (
        f"Brief: {state['brief']}\n"
        f"Relevant trend signals:\n{context}\n"
        "Propose two or three concept directions and a short list of "
        "suitable materials. Be concise and concrete."
    )
    state["proposal"] = llm.invoke(prompt).content
    return state


def build_graph():
    graph = StateGraph(TrendState)
    graph.add_node("retrieve_signals", retrieve_signals)
    graph.add_node("synthesise_proposal", synthesise_proposal)
    graph.set_entry_point("retrieve_signals")
    graph.add_edge("retrieve_signals", "synthesise_proposal")
    graph.add_edge("synthesise_proposal", END)
    return graph.compile()


class TrendAgentModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        self.graph = build_graph()

    def predict(self, context, model_input):
        brief = model_input["brief"][0]
        result = self.graph.invoke({"brief": brief, "retrieved_signals": [], "proposal": ""})
        return result["proposal"]


model = TrendAgentModel()
