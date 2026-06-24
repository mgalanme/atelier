"""
Registra un único endpoint consolidado con todos los agentes
(trend, sustainability, storytelling, buyer) como served entities.
Consume solo 1 endpoint de la cuota de Free Edition.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

ENDPOINT_NAME = "atelier-agents"
CATALOG = "atelier"
SCHEMA = "gold"
MODEL_NAMES = [
    "trend_agent",
    "sustainability_agent",
    "storytelling_agent",
    "buyer_agent",  # Si aún no está registrado, se omitirá
]


def get_latest_version(model_name):
    """Obtiene la versión más reciente del modelo registrado en Unity Catalog."""
    client = WorkspaceClient()
    full_name = f"{CATALOG}.{SCHEMA}.{model_name}"
    try:
        # Método que funciona en la versión del SDK que tienes
        versions = client.model_versions.list_by_model(model_name=full_name)
        version_list = list(versions)
        if version_list:
            sorted_versions = sorted(version_list, key=lambda v: int(v.version), reverse=True)
            return sorted_versions[0].version
    except Exception as e:
        print(f"Error retrieving versions for {model_name}: {e}")
    return None


def deploy_consolidated_endpoint():
    client = WorkspaceClient()
    served_entities = []

    for model_name in MODEL_NAMES:
        version = get_latest_version(model_name)
        if version is None:
            print(f"⚠️ Model 'atelier.gold.{model_name}' not registered yet. Skipping.")
            continue
        entity_name = f"{CATALOG}.{SCHEMA}.{model_name}"
        served_entities.append(
            ServedEntityInput(
                entity_name=entity_name,
                entity_version=version,
                workload_size="Small",
                scale_to_zero_enabled=True,
            )
        )

    if not served_entities:
        print("❌ No models found to deploy. Aborting.")
        return

    for se in served_entities:
        print(f"✅ Deploying: {se.entity_name} version {se.entity_version}")

    try:
        _ = client.serving_endpoints.get(ENDPOINT_NAME)
        print(f"Updating existing endpoint '{ENDPOINT_NAME}'...")
        client.serving_endpoints.update_config_and_wait(
            name=ENDPOINT_NAME,
            served_entities=served_entities,
        )
        print(f"Endpoint '{ENDPOINT_NAME}' updated successfully.")
    except Exception:
        print(f"Creating new endpoint '{ENDPOINT_NAME}'...")
        client.serving_endpoints.create_and_wait(
            name=ENDPOINT_NAME,
            config=EndpointCoreConfigInput(served_entities=served_entities),
            timeout=600,
        )
        print(f"Endpoint '{ENDPOINT_NAME}' created successfully.")


if __name__ == "__main__":
    deploy_consolidated_endpoint()
