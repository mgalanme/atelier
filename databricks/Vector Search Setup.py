# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# dependencies = [
#   "databricks-vectorsearch",
#   "python-dotenv",
# ]
# ///
# DBTITLE 1,Install dependencies
# MAGIC %pip install databricks-vectorsearch python-dotenv

# COMMAND ----------

# DBTITLE 1,Load environment and configure
import os
from databricks.vector_search.client import VectorSearchClient
from dotenv import load_dotenv

load_dotenv()

CATALOG = os.environ.get("ATELIER_CATALOG", "atelier")
GOLD_SCHEMA = os.environ.get("ATELIER_SCHEMA_GOLD", "gold")
ENDPOINT_NAME = "atelier-vector-search"
SOURCE_TABLE = f"{CATALOG}.{GOLD_SCHEMA}.trend_documents"
INDEX_NAME = f"{CATALOG}.{GOLD_SCHEMA}.trend_documents_index"

# COMMAND ----------

# DBTITLE 1,Create endpoint and index
client = VectorSearchClient()

# Create endpoint if it doesn't exist
existing_endpoints = [e["name"] for e in client.list_endpoints().get("endpoints", [])]
if ENDPOINT_NAME not in existing_endpoints:
    client.create_endpoint(name=ENDPOINT_NAME, endpoint_type="STANDARD")
    print(f"Endpoint {ENDPOINT_NAME} created.")
else:
    print(f"Endpoint {ENDPOINT_NAME} already exists.")

# Enable Change Data Feed on source table (required for Vector Search)
spark.sql(f"ALTER TABLE {SOURCE_TABLE} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
print(f"Change Data Feed enabled on {SOURCE_TABLE}")

# Create index if it doesn't exist; otherwise sync it
if client.index_exists(index_name=INDEX_NAME):
    index = client.get_index(endpoint_name=ENDPOINT_NAME, index_name=INDEX_NAME)
    index_status = index.describe().get('status', {})
    if index_status.get('ready', False):
        index.sync()
        print(f"Index {INDEX_NAME} already existed; sync triggered.")
    else:
        print(f"Index {INDEX_NAME} exists but is not ready yet.")
        print(f"Status: {index_status.get('message', 'Provisioning in progress')}")
        print("Wait for provisioning to complete before syncing.")
else:
    client.create_delta_sync_index(
        endpoint_name=ENDPOINT_NAME,
        index_name=INDEX_NAME,
        source_table_name=SOURCE_TABLE,
        pipeline_type="TRIGGERED",
        primary_key="document_id",
        embedding_source_column="document_text",
        embedding_model_endpoint_name="databricks-gte-large-en",
    )
    print(f"Index {INDEX_NAME} created for the first time.")
