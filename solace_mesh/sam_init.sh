#!/usr/bin/env bash
# WHAT: initialises the Solace Agent Mesh project for ATELIER, pointing it
#       at the self-hosted broker started by docker-compose.broker.yml and
#       at the Mosaic AI LLM endpoint as its reasoning model.
# WHY:  keeps SAM's own reasoning calls on the same governed Mosaic AI
#       Model Serving endpoint used by every specialist agent, rather than
#       introducing a second, ungoverned model provider.
# HOW:  run once, from this folder, after the broker is up and the .env
#       file at the project root has been filled in.
set -euo pipefail

source ../.env

sam init --skip \
  --namespace "${SOLACE_NAMESPACE}" \
  --broker-type "external" \
  --broker-url "${SOLACE_BROKER_URL}" \
  --broker-vpn "${SOLACE_VPN}" \
  --broker-username "${SOLACE_USERNAME}" \
  --broker-password "${SOLACE_PASSWORD}" \
  --llm-service-endpoint "${MOSAIC_LLM_ENDPOINT}" \
  --llm-service-api-key "${DATABRICKS_TOKEN}" \
  --llm-service-planning-model-name "databricks/atelier-llm" \
  --llm-service-general-model-name "databricks/atelier-llm" \
  --add-rest-gateway

echo "SAM initialised. Copy the YAML files from configs/agents into the"
echo "generated .solace/agents/ folder before running 'sam run'."
