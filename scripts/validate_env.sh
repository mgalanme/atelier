#!/usr/bin/env bash
# WHAT: checks that the variables every other script depends on are set.
# WHY:  fails fast and clearly, instead of letting a script fail deep inside
#       a Databricks or Solace call with a confusing error.
# HOW:  run from the project root: ./scripts/validate_env.sh
set -euo pipefail

REQUIRED_VARS=(
  DATABRICKS_HOST DATABRICKS_HTTP_PATH DATABRICKS_TOKEN
  ATELIER_CATALOG ATELIER_SCHEMA_BRONZE ATELIER_SCHEMA_SILVER ATELIER_SCHEMA_GOLD
  MOSAIC_LLM_ENDPOINT SOLACE_BROKER_URL SOLACE_USERNAME SOLACE_PASSWORD
)

if [ ! -f .env ]; then
  echo "Missing .env file. Copy .env.example to .env and fill in the values."
  exit 1
fi

set -a
source .env
set +a

missing=0
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "Missing or empty: ${var}"
    missing=1
  fi
done

if [ "$missing" -eq 1 ]; then
  exit 1
fi

echo "Environment looks complete."
