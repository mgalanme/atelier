"""
Registra un único endpoint consolidado con todos los agentes
(trend, sustainability, storytelling, buyer) como served entities.
Consume solo 1 endpoint de la cuota de Free Edition, no 4.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

ENDPOINT_NAME = "atelier-agents"
CATALOG = "atelier"
SCHEMA = "gold"

# Nombre corto y predecible de cada entidad servida, para poder
# consultarlas por separado más adelante (/served-models/<name>/invocations).
SERVED_NAMES = {
    "trend_agent": "trend",
    "sustainability_agent": "sustainability",
    "storytelling_agent": "storytelling",
    "buyer_agent": "buyer",  # se omitirá hasta que exista
}


def get_latest_version(client, model_name):
    """Obtiene la versión más reciente del modelo registrado en Unity Catalog."""
    full_name = f"{CATALOG}.{SCHEMA}.{model_name}"
    try:
        versions = list(client.model_versions.list(full_name=full_name))
        if versions:
            return sorted(versions, key=lambda v: int(v.version), reverse=True)[0].version
    except Exception as e:
        print(f"Error retrieving versions for {model_name}: {e}")
    return None


def deploy_consolidated_endpoint():
    client = WorkspaceClient()
    served_entities = []

    for model_name, served_name in SERVED_NAMES.items():
        version = get_latest_version(client, model_name)
        if version is None:
            print(f"⚠️ Model 'atelier.gold.{model_name}' not registered yet. Skipping.")
            continue
        served_entities.append(
            ServedEntityInput(
                name=served_name,
                entity_name=f"{CATALOG}.{SCHEMA}.{model_name}",
                entity_version=version,
                workload_size="Small",
                scale_to_zero_enabled=True,
            )
        )

    if not served_entities:
        print("❌ No models found to deploy. Aborting.")
        return

    for se in served_entities:
        print(f"✅ Deploying: {se.name} -> {se.entity_name} version {se.entity_version}")

    try:
        client.serving_endpoints.get(ENDPOINT_NAME)
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
