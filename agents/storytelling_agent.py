"""
Storytelling agent: generates draft narrative and positioning content for an
approved concept, aligned with the stated target audience and brand voice.
"""

import os

import mlflow
from databricks_langchain import ChatDatabricks
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

# Use environment variable with fallback
LLM_ENDPOINT = os.environ.get("ATELIER_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")


class StorytellingState(TypedDict):
    concept: str
    target_audience: str
    narrative: str


def draft_narrative(state: StorytellingState) -> StorytellingState:
    llm = ChatDatabricks(endpoint=LLM_ENDPOINT)
    prompt = (
        f"Concept: {state['concept']}\n"
        f"Target audience: {state['target_audience']}\n"
        "Write a short, evocative collection narrative and a one-line "
        "positioning statement suitable for a technical specification sheet."
    )
    state["narrative"] = llm.invoke(prompt).content
    return state


def build_graph():
    graph = StateGraph(StorytellingState)
    graph.add_node("draft_narrative", draft_narrative)
    graph.set_entry_point("draft_narrative")
    graph.add_edge("draft_narrative", END)
    return graph.compile()


class StorytellingAgentModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        self.graph = build_graph()

    def predict(self, context, model_input):
        row = model_input.iloc[0]
        result = self.graph.invoke(
            {
                "concept": row["concept"],
                "target_audience": row["target_audience"],
                "narrative": "",
            }
        )
        return result["narrative"]


# Expose the model for MLflow Models-as-Code
model = StorytellingAgentModel()
mlflow.models.set_model(model)
