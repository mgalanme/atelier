"""
Sustainability agent: evaluates a proposed concept and material list against
circularity targets and the regulatory constraints relevant to the target
markets, surfacing concrete substitution suggestions rather than a bare
pass or fail.
"""

import os
from typing import List

import mlflow
from databricks_langchain import ChatDatabricks
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

# Use environment variable with fallback
LLM_ENDPOINT = os.environ.get("ATELIER_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")


class SustainabilityState(TypedDict):
    concept: str
    materials: List[str]
    target_markets: List[str]
    assessment: str


def assess(state: SustainabilityState) -> SustainabilityState:
    llm = ChatDatabricks(endpoint=LLM_ENDPOINT)
    prompt = (
        f"Concept: {state['concept']}\n"
        f"Materials: {', '.join(state['materials'])}\n"
        f"Target markets: {', '.join(state['target_markets'])}\n"
        "Assess circularity and regulatory fit for these markets. Flag any "
        "material that should be substituted and suggest an alternative."
    )
    state["assessment"] = llm.invoke(prompt).content
    return state


def build_graph():
    graph = StateGraph(SustainabilityState)
    graph.add_node("assess", assess)
    graph.set_entry_point("assess")
    graph.add_edge("assess", END)
    return graph.compile()


class SustainabilityAgentModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        self.graph = build_graph()

    def predict(self, context, model_input):
        row = model_input.iloc[0]
        result = self.graph.invoke(
            {
                "concept": row["concept"],
                "materials": row["materials"],
                "target_markets": row["target_markets"],
                "assessment": "",
            }
        )
        return result["assessment"]


# Expose the model for MLflow Models-as-Code
model = SustainabilityAgentModel()
mlflow.models.set_model(model)
