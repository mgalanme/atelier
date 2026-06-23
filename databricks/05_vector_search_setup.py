# Databricks notebook source
# MAGIC %pip install databricks-vectorsearch python-dotenv

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

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

    # Change Data Feed es un requisito de Vector Search sobre la tabla
    # fuente. Activarlo es idempotente (solo cambia una propiedad de
    # tabla, no toca los datos), así que es seguro repetirlo cada vez.
    spark.sql(f"ALTER TABLE {SOURCE_TABLE} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    print(f"Change Data Feed activado en {SOURCE_TABLE}.")

    # Crear el índice solo si no existe; si ya existe, sincronizarlo solo
    # cuando está listo. create_delta_sync_index no es idempotente: falla
    # si el índice ya existe.
    if client.index_exists(index_name=INDEX_NAME):
        index = client.get_index(endpoint_name=ENDPOINT_NAME, index_name=INDEX_NAME)
        status = index.describe().get("status", {})
        if status.get("ready", False):
            index.sync()
            print(f"Índice {INDEX_NAME} ya existía; sincronización lanzada.")
        else:
            print(f"Índice {INDEX_NAME} existe pero aún no está listo.")
            print(f"Estado: {status.get('message', 'Aprovisionamiento en curso')}")
            print("Espera a que termine de aprovisionarse antes de sincronizar.")
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
        print(f"Índice {INDEX_NAME} creado por primera vez.")


if __name__ == "__main__":
    main()
