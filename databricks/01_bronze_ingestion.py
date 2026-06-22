"""
Bronze ingestion: lands raw source data into the atelier.bronze schema.

Sources landed here are intentionally left close to their original shape.
No business logic, validation or deduplication happens at this stage; that
is deferred to the Silver notebook, so that a change in business rules never
requires re-pulling from the source system.
"""

import os
import random
import uuid
from datetime import datetime, timedelta

from dotenv import load_dotenv

from databricks import sql

load_dotenv()

CATALOG = os.environ.get("ATELIER_CATALOG", "atelier")
BRONZE_SCHEMA = os.environ.get("ATELIER_SCHEMA_BRONZE", "bronze")

BRONZE_TABLES = {
    "trend_signals_raw": [
        "signal_id", "source", "season", "colour", "silhouette",
        "captured_at", "payload"
    ],
    "inventory_raw": [
        "sku", "warehouse", "quantity_on_hand", "as_of_date", "payload"
    ],
    "sales_history_raw": [
        "order_id", "sku", "market", "units_sold", "sale_date", "payload"
    ],
    "climate_raw": [
        "region", "season", "avg_temp_c", "avg_rainfall_mm", "captured_at"
    ],
    "social_listening_raw": [
        "post_id", "platform", "captured_at", "sentiment_score", "payload"
    ],
}


def get_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def ensure_bronze_tables(cursor):
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{BRONZE_SCHEMA}")
    for table_name, columns in BRONZE_TABLES.items():
        column_defs = ", ".join(f"{c} STRING" for c in columns)
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {CATALOG}.{BRONZE_SCHEMA}.{table_name} "
            f"({column_defs}, ingestion_run_id STRING, ingested_at TIMESTAMP)"
        )


def ingest_batch(cursor, table_name, rows: list[dict]):
    """
    Append-only ingestion. A fresh UUID4 run id tags every batch so that a
    failed or partial run can be identified and purged without touching
    rows from any other run.
    """
    run_id = str(uuid.uuid4())
    columns = BRONZE_TABLES[table_name]
    for row in rows:
        # Escape single quotes and build the VALUES clause
        escaped_values = []
        for c in columns:
            val = str(row.get(c, ""))
            val_escaped = val.replace(chr(39), chr(39) * 2)
            escaped_values.append(f"'{val_escaped}'")
        values_clause = ", ".join(escaped_values)
        cursor.execute(
            f"INSERT INTO {CATALOG}.{BRONZE_SCHEMA}.{table_name} "
            f"({', '.join(columns)}, ingestion_run_id, ingested_at) "
            f"VALUES ({values_clause}, '{run_id}', current_timestamp())"
        )
    return run_id


if __name__ == "__main__":

    # ---------- 1. Synthetic trend signals ----------
    trend_signals = []
    sources = ["WGSN", "Vogue Runway", "Pantone", "Trendstop", "Instagram"]
    seasons = ["Spring/Summer", "Fall/Winter", "Pre-Fall", "Resort"]
    colours = ["Pastel", "Neon", "Earth tones", "Monochrome", "Metallic"]
    silhouettes = ["Oversize", "Tailored", "Flowing", "Boxy", "Asymmetric"]
    regions = ["Global", "Europe", "Americas", "Asia"]

    for i in range(100):
        trend_signals.append({
            "signal_id": f"TR-{i:04d}",
            "source": random.choice(sources),
            "season": random.choice(seasons),
            "colour": random.choice(colours),
            "silhouette": random.choice(silhouettes),
            "captured_at": (
                datetime.now() - timedelta(days=random.randint(0, 180))
            ).isoformat(),
            "payload": (
                f'{{"confidence": {round(random.uniform(0.6, 0.95), 2)}, '
                f'"region": "{random.choice(regions)}"}}'
            )
        })

    # ---------- 2. Synthetic inventory ----------
    inventory = []
    warehouses = ["MAD", "BCN", "LIS", "PAR", "NYC", "LON", "MIL"]
    for i in range(200):
        inventory.append({
            "sku": f"SKU-{i:05d}",
            "warehouse": random.choice(warehouses),
            "quantity_on_hand": str(random.randint(0, 500)),
            "as_of_date": (
                datetime.now() - timedelta(days=random.randint(0, 30))
            ).date().isoformat(),
            "payload": (
                f'{{"batch": "B{random.randint(2024, 2026)}-'
                f'{random.randint(1, 12):02d}"}}'
            )
        })

    # ---------- 3. Synthetic sales history ----------
    sales_history = []
    markets = ["ES", "FR", "IT", "DE", "UK", "US", "JP", "BR"]
    channels = ["online", "retail", "pop-up"]
    for i in range(300):
        sales_history.append({
            "order_id": f"ORD-{i:06d}",
            "sku": f"SKU-{random.randint(0, 199):05d}",
            "market": random.choice(markets),
            "units_sold": str(random.randint(1, 50)),
            "sale_date": (
                datetime.now() - timedelta(days=random.randint(0, 365))
            ).date().isoformat(),
            "payload": f'{{"channel": "{random.choice(channels)}"}}'
        })

    # ---------- 4. Synthetic climate data ----------
    climate = []
    climate_regions = ["North", "South", "East", "West"]
    climate_seasons = ["Spring", "Summer", "Fall", "Winter"]
    for region in climate_regions:
        for season in climate_seasons:
            climate.append({
                "region": region,
                "season": season,
                "avg_temp_c": str(round(random.uniform(5, 30), 1)),
                "avg_rainfall_mm": str(round(random.uniform(10, 200), 1)),
                "captured_at": datetime.now().isoformat()
            })

    # ---------- 5. Synthetic social listening ----------
    social_listening = []
    platforms = ["Instagram", "TikTok", "Pinterest", "YouTube", "X"]
    hashtags = ["#fashion", "#style", "#trend", "#ootd"]
    languages = ["en", "es", "fr", "it"]
    for i in range(150):
        social_listening.append({
            "post_id": f"POST-{i:06d}",
            "platform": random.choice(platforms),
            "captured_at": (
                datetime.now() - timedelta(hours=random.randint(1, 720))
            ).isoformat(),
            "sentiment_score": str(round(random.uniform(-1, 1), 2)),
            "payload": (
                f'{{"hashtags": ["{random.choice(hashtags)}"], '
                f'"language": "{random.choice(languages)}"}}'
            )
        })

    # ---------- Execute ingestion ----------
    connection = get_connection()
    with connection.cursor() as cursor:
        ensure_bronze_tables(cursor)
        ingest_batch(cursor, "trend_signals_raw", trend_signals)
        ingest_batch(cursor, "inventory_raw", inventory)
        ingest_batch(cursor, "sales_history_raw", sales_history)
        ingest_batch(cursor, "climate_raw", climate)
        ingest_batch(cursor, "social_listening_raw", social_listening)
    connection.close()
