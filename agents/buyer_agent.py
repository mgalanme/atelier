"""
Buyer agent: combines the demand forecast model registered in
databricks/06_predictive_models_mlflow.py with current inventory data to
produce a feasibility and budget commentary on a proposed concept.
"""

import os

import mlflow
from langchain_community.chat_models import ChatDatabricks
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


class BuyerState(TypedDict):
    concept: str
    forecast_summary: str
    inventory_summary: str
    commentary: str


def build_commentary(state: BuyerState) -> BuyerState:
    llm = ChatDatabricks(endpoint=os.environ["MOSAIC_LLM_ENDPOINT"])
    prompt = (
        f"Concept: {state['concept']}\n"
        f"Demand forecast summary: {state['forecast_summary']}\n"
        f"Inventory and supply summary: {state['inventory_summary']}\n"
        "Comment on commercial feasibility, suggested volumes by market, "
        "and any budget or supply risk worth flagging to the buyer."
    )
    state["commentary"] = llm.invoke(prompt).content
    return state


def build_graph():
    graph = StateGraph(BuyerState)
    graph.add_node("build_commentary", build_commentary)
    graph.set_entry_point("build_commentary")
    graph.add_edge("build_commentary", END)
    return graph.compile()


class BuyerAgentModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        self.graph = build_graph()

    def predict(self, context, model_input):
        row = model_input.iloc[0]
        result = self.graph.invoke({
            "concept": row["concept"],
            "forecast_summary": row["forecast_summary"],
            "inventory_summary": row["inventory_summary"],
            "commentary": "",
        })
        return result["commentary"]


model = BuyerAgentModel()
