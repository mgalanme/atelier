"""
Registra un único endpoint consolidado con todos los agentes
(trend, sustainability, storytelling, buyer) como served entities.
Consume solo 1 endpoint de la cuota de Free Edition, no 4.
"""

from datetime import timedelta

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, OperationFailed
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput,
    ServedEntityInput,
    TrafficConfig,
    Route,
)

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

    # Create traffic config with equal distribution
    n = len(served_entities)
    base_pct = 100 // n
    remainder = 100 % n
    routes = []
    for i, se in enumerate(served_entities):
        pct = base_pct + (1 if i < remainder else 0)
        routes.append(Route(served_model_name=se.name, traffic_percentage=pct))
    traffic_config = TrafficConfig(routes=routes)

    try:
        client.serving_endpoints.get(ENDPOINT_NAME)
        print(f"Updating existing endpoint '{ENDPOINT_NAME}'...")
        client.serving_endpoints.update_config_and_wait(
            name=ENDPOINT_NAME,
            served_entities=served_entities,
            traffic_config=traffic_config,
        )
        print(f"Endpoint '{ENDPOINT_NAME}' updated successfully.")
    except OperationFailed as e:
        # Retrieve detailed error from endpoint state
        print(f"\n❌ Endpoint update failed: {e}\n")
        endpoint = client.serving_endpoints.get(ENDPOINT_NAME)
        if endpoint.state and endpoint.state.config_update:
            print(f"Config update state: {endpoint.state.config_update}")
        
        print("\n⚠️  DIAGNOSIS: This is likely a Free Edition workspace limitation.")
        print("Free Edition does not support multiple served entities in a single endpoint.")
        print("\n📋 Your options:")
        print("  1. Deploy only ONE model per endpoint (defeats the consolidation purpose)")
        print("  2. Upgrade to a paid workspace tier that supports multi-entity endpoints")
        print("  3. Accept the endpoint quota limit and deploy fewer models")
        print("\nThe configuration you attempted requires platform features not available in Free Edition.")
        return  # Don't re-raise, just exit
    except NotFound:
        print(f"Creating new endpoint '{ENDPOINT_NAME}'...")
        try:
            client.serving_endpoints.create_and_wait(
                name=ENDPOINT_NAME,
                config=EndpointCoreConfigInput(
                    served_entities=served_entities,
                    traffic_config=traffic_config,
                ),
                timeout=timedelta(seconds=600),
            )
            print(f"Endpoint '{ENDPOINT_NAME}' created successfully.")
        except OperationFailed as e:
            print(f"\n❌ Endpoint creation failed: {e}")
            print("\n⚠️  This likely indicates a Free Edition limitation.")
            print("Multiple served entities may not be supported in your workspace tier.")
            return


if __name__ == "__main__":
    deploy_consolidated_endpoint()
