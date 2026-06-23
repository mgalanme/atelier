"""
Registra y despliega el agente de tendencias como primer agente real (no
desechable) de Mosaic AI Model Serving. Cuando esto funcione de extremo a
extremo, se replica el mismo patrón para los otros tres en
register_mosaic_agents.py.

Usa el patrón Models-as-Code (python_model como ruta de fichero) y declara
el endpoint del LLM como recurso, para que Databricks aprovisione
credenciales automáticamente al desplegar (no hace falta pasar un token).
"""

import os

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
mlflow.set_experiment("/Users/mgalanme@gmail.com/atelier/agents")

AGENT_FILE = os.path.join(os.path.dirname(__file__), "trend_agent.py")


def register_and_deploy():
    # Logear el modelo con este input_example ejecuta el agente una vez de
    # verdad (llama al LLM de verdad) para inferir la firma. Es intencional:
    # valida el flujo completo antes incluso de desplegar.
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
    print(f"Endpoint '{ENDPOINT_NAME}' creado correctamente.")


if __name__ == "__main__":
    register_and_deploy()
