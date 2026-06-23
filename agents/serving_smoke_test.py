"""
Serving smoke test: comprueba si Databricks Free Edition permite desplegar
un Model Serving endpoint personalizado, antes de invertir esfuerzo en
register_mosaic_agents.py. Registra un modelo trivial (eco) y prueba a
desplegarlo como endpoint CPU con scale-to-zero.

Desechable: una vez resuelta la pregunta, borra el endpoint y, si quieres,
también el modelo registrado.
"""

import uuid as py_uuid

import mlflow
from databricks.sdk import WorkspaceClient

CATALOG = "atelier"
GOLD_SCHEMA = "gold"
MODEL_NAME = f"{CATALOG}.{GOLD_SCHEMA}.smoke_test_model"
ENDPOINT_NAME = "atelier-smoke-test"

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/atelier/serving_smoke_test")


class EchoModel(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input):
        return model_input


def register_and_deploy():
    with mlflow.start_run(run_name=f"smoke-test-{py_uuid.uuid4()}"):
        model_info = mlflow.pyfunc.log_model(python_model=EchoModel(), artifact_path="model")
        registered = mlflow.register_model(model_info.model_uri, MODEL_NAME)

    client = WorkspaceClient()
    client.serving_endpoints.create_and_wait(
        name=ENDPOINT_NAME,
        config={
            "served_entities": [
                {
                    "entity_name": MODEL_NAME,
                    "entity_version": registered.version,
                    "workload_size": "Small",
                    "scale_to_zero_enabled": True,
                }
            ]
        },
    )
    print(f"Smoke test endpoint '{ENDPOINT_NAME}' creado correctamente.")


def cleanup():
    """Llama a esto aparte, cuando ya tengas la respuesta y quieras borrar el endpoint."""
    client = WorkspaceClient()
    client.serving_endpoints.delete(name=ENDPOINT_NAME)
    print(f"Endpoint '{ENDPOINT_NAME}' eliminado.")


if __name__ == "__main__":
    register_and_deploy()
