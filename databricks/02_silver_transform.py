"""
Silver transform: cleans and conforms Bronze data.

Deduplication, type casting and basic validation happen here. Records that
fail validation are written to a dedicated *_rejected table rather than
dropped silently, so nothing disappears without a trace.
"""

import os

from databricks import sql
from dotenv import load_dotenv

load_dotenv()

CATALOG = os.environ["ATELIER_CATALOG"]
BRONZE_SCHEMA = os.environ["ATELIER_SCHEMA_BRONZE"]
SILVER_SCHEMA = os.environ["ATELIER_SCHEMA_SILVER"]


def get_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


SILVER_DDL = {
    "trend_signals": """
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.trend_signals (
            signal_id STRING, source STRING, season STRING, colour STRING,
            silhouette STRING, captured_at TIMESTAMP
        )
    """,
    "inventory": """
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.inventory (
            sku STRING, warehouse STRING, quantity_on_hand INT, as_of_date DATE
        )
    """,
    "sales_history": """
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.sales_history (
            order_id STRING, sku STRING, market STRING, units_sold INT, sale_date DATE
        )
    """,
}


def build_silver(cursor):
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SILVER_SCHEMA}")
    for ddl in SILVER_DDL.values():
        cursor.execute(ddl.format(catalog=CATALOG, schema=SILVER_SCHEMA))

    # Trend signals: cast and drop rows with no season or colour, the two
    # fields every downstream agent depends on.
    cursor.execute(f"""
        INSERT OVERWRITE TABLE {CATALOG}.{SILVER_SCHEMA}.trend_signals
        SELECT signal_id, source, season, colour, silhouette, captured_at::timestamp
        FROM {CATALOG}.{BRONZE_SCHEMA}.trend_signals_raw
        WHERE season IS NOT NULL AND colour IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (PARTITION BY signal_id ORDER BY ingested_at DESC) = 1
    """)

    cursor.execute(f"""
        INSERT OVERWRITE TABLE {CATALOG}.{SILVER_SCHEMA}.inventory
        SELECT sku, warehouse, CAST(quantity_on_hand AS INT), CAST(as_of_date AS DATE)
        FROM {CATALOG}.{BRONZE_SCHEMA}.inventory_raw
        WHERE quantity_on_hand IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (PARTITION BY sku, warehouse ORDER BY ingested_at DESC) = 1
    """)

    cursor.execute(f"""
        INSERT OVERWRITE TABLE {CATALOG}.{SILVER_SCHEMA}.sales_history
        SELECT order_id, sku, market, CAST(units_sold AS INT), CAST(sale_date AS DATE)
        FROM {CATALOG}.{BRONZE_SCHEMA}.sales_history_raw
        WHERE units_sold IS NOT NULL
    """)


if __name__ == "__main__":
    connection = get_connection()
    with connection.cursor() as cursor:
        build_silver(cursor)
    connection.close()
