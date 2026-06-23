"""
Creates the Mosaic AI Vector Search endpoint and index used by the trend
synthesis and sustainability agents for semantic retrieval over historical
collections, trend descriptions and sustainability documentation.

Run inside a Databricks notebook with the databricks-vectorsearch client
available; this is not a plain local script.
"""

import os

from databricks.vector_search.client import VectorSearchClient
from dotenv import load_dotenv

load_dotenv()

CATALOG = os.environ.get("ATELIER_CATALOG", "atelier")
GOLD_SCHEMA = os.environ.get("ATELIER_SCHEMA_GOLD", "gold")
ENDPOINT_NAME = "atelier-vector-search"
SOURCE_TABLE = f"{CATALOG}.{GOLD_SCHEMA}.trend_documents"
INDEX_NAME = f"{CATALOG}.{GOLD_SCHEMA}.trend_documents_index"


def main():
    client = VectorSearchClient()

    # Crear endpoint si no existe
    existing_endpoints = [e["name"] for e in client.list_endpoints().get("endpoints", [])]
    if ENDPOINT_NAME not in existing_endpoints:
        client.create_endpoint(name=ENDPOINT_NAME, endpoint_type="STANDARD")
        print(f"Endpoint {ENDPOINT_NAME} creado.")
    else:
        print(f"Endpoint {ENDPOINT_NAME} ya existe.")

    # Crear índice sincronizado con la tabla Gold
    client.create_delta_sync_index(
        endpoint_name=ENDPOINT_NAME,
        index_name=INDEX_NAME,
        source_table_name=SOURCE_TABLE,
        pipeline_type="TRIGGERED",
        primary_key="document_id",
        embedding_source_column="document_text",
        embedding_model_endpoint_name="databricks-gte-large-en",
    )
    print(f"Índice {INDEX_NAME} creado/actualizado.")


if __name__ == "__main__":
    main()
