"""
Trend synthesis agent: given a creative brief, retrieves relevant historical
and current trend signals via Mosaic AI Vector Search and proposes concept
directions and material recommendations.

Empaquetado con el patrón MLflow Models-as-Code: este fichero se registra
por ruta, no como objeto Python serializado, y llama a
mlflow.models.set_model(model) al final para que MLflow sepa qué objeto
cargar cuando este mismo fichero se vuelva a ejecutar dentro del
contenedor de serving.
"""

import os
from typing import List, TypedDict

import mlflow
from databricks_langchain import ChatDatabricks
from langgraph.graph import END, StateGraph

LLM_ENDPOINT = os.environ.get("ATELIER_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")


class TrendState(TypedDict):
    brief: str
    retrieved_signals: List[str]
    proposal: str


def retrieve_signals(state: TrendState) -> TrendState:
    # TODO: sustituir por una llamada real al índice atelier-vector-search
    # (databricks/05_vector_search_setup.py). Se deja vacío a propósito;
    # no bloquea esta primera puesta en marcha.
    state["retrieved_signals"] = []
    return state


def synthesise_proposal(state: TrendState) -> TrendState:
    llm = ChatDatabricks(endpoint=LLM_ENDPOINT)
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
        return [result["proposal"]]


model = TrendAgentModel()
mlflow.models.set_model(model)
