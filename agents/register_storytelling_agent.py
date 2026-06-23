"""
Registers and deploys the storytelling agent as a Mosaic AI Model Serving endpoint.
"""

import os
import subprocess
import sys

import mlflow
import pandas as pd
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput
from mlflow.models.resources import DatabricksServingEndpoint

CATALOG = "atelier"
GOLD_SCHEMA = "gold"
MODEL_NAME = f"{CATALOG}.{GOLD_SCHEMA}.storytelling_agent"
ENDPOINT_NAME = "atelier-storytelling-agent"
LLM_ENDPOINT = os.environ.get("ATELIER_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Users/mgalanme@gmail.com/atelier/agents_experiment")

AGENT_FILE = os.path.join(os.getcwd(), "storytelling_agent.py")

# Install required packages
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "databricks-langchain", "langgraph"]
)


def register_and_deploy():
    input_example = pd.DataFrame(
        {
            "concept": [
                "A spring/summer capsule collection inspired by Mediterranean "
                "coastal towns, pastel palette, relaxed tailoring."
            ],
            "target_audience": ["Young professionals aged 25-35, eco-conscious, urban lifestyle"],
        }
    )

    with mlflow.start_run(run_name="register-storytelling-agent"):
        model_info = mlflow.pyfunc.log_model(
            python_model=AGENT_FILE,
            name="agent",
            input_example=input_example,
            resources=[DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT)],
            pip_requirements=["langgraph", "databricks-langchain"],
        )
        registered = mlflow.register_model(model_info.model_uri, MODEL_NAME)

    client = WorkspaceClient()
    client.serving_endpoints.create_and_wait(
        name=ENDPOINT_NAME,
        config=EndpointCoreConfigInput(
            served_entities=[
                ServedEntityInput(
                    entity_name=MODEL_NAME,
                    entity_version=registered.version,
                    workload_size="Small",
                    scale_to_zero_enabled=True,
                )
            ]
        ),
    )
    print(f"Endpoint '{ENDPOINT_NAME}' created successfully.")


if __name__ == "__main__":
    register_and_deploy()
