"""
Registers and deploys the four specialist agents to Mosaic AI Model Serving,
using the Models-as-Code pattern: each agent module already exposes a
top-level `model` object, so mlflow.models.set_model is the only step
needed before logging and registering it.

LESSON LEARNED (reused from earlier case studies): a fresh UUID4 run name is
used for every registration call, since Databricks Free Edition MLflow
becomes unreliable after a small number of start_run calls within one
session.
"""

import uuid

import buyer_agent
import mlflow
import storytelling_agent
import sustainability_agent
import trend_agent
from databricks.sdk import WorkspaceClient

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/atelier/agents")

AGENT_MODULES = {
    "atelier-trend-agent": trend_agent,
    "atelier-sustainability-agent": sustainability_agent,
    "atelier-storytelling-agent": storytelling_agent,
    "atelier-buyer-agent": buyer_agent,
}


def register_and_deploy(endpoint_name: str, module) -> str:
    mlflow.models.set_model(module.model)
    with mlflow.start_run(run_name=f"register-{endpoint_name}-{uuid.uuid4()}"):
        model_info = mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model=module.model,
        )
        registered = mlflow.register_model(model_info.model_uri, f"atelier.gold.{endpoint_name}")

    client = WorkspaceClient()
    client.serving_endpoints.create_and_wait(
        name=endpoint_name,
        config={
            "served_entities": [
                {
                    "entity_name": f"atelier.gold.{endpoint_name}",
                    "entity_version": registered.version,
                    "workload_size": "Small",
                    "scale_to_zero_enabled": True,
                }
            ]
        },
    )
    return endpoint_name


if __name__ == "__main__":
    for endpoint_name, module in AGENT_MODULES.items():
        register_and_deploy(endpoint_name, module)
