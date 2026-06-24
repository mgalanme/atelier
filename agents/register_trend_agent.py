"""
Registra y despliega el agente de tendencias real, con Models-as-Code y
autenticación automática hacia el endpoint del LLM declarado como recurso.
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
MODEL_NAME = f"{CATALOG}.{GOLD_SCHEMA}.trend_agent"
ENDPOINT_NAME = "atelier-trend-agent"
LLM_ENDPOINT = os.environ.get("ATELIER_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Users/mgalanme@gmail.com/atelier/agents_experiment")

AGENT_FILE = os.path.join(os.getcwd(), "trend_agent.py")

# typing_extensions primero, con upgrade, antes de las dependencias que
# trend_agent.py necesita cuando MLflow lo ejecute para inferir la firma.
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "--upgrade", "typing_extensions>=4.6.0"]
)
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "databricks-langchain", "langgraph"]
)


def register_and_deploy():
    # Logear el modelo con este input_example ejecuta el agente una vez de
    # verdad (llama al LLM de verdad) para inferir la firma.
    input_example = pd.DataFrame(
        {
            "brief": [
                "A spring/summer capsule collection inspired by Mediterranean "
                "coastal towns, pastel palette, relaxed tailoring."
            ]
        }
    )

    with mlflow.start_run(run_name="register-trend-agent"):
        model_info = mlflow.pyfunc.log_model(
            python_model=AGENT_FILE,
            name="agent",
            input_example=input_example,
            resources=[DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT)],
            pip_requirements=["typing_extensions>=4.6.0", "langgraph", "databricks-langchain"],
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
    print(f"Endpoint '{ENDPOINT_NAME}' creado correctamente.")


if __name__ == "__main__":
    register_and_deploy()
