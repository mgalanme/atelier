"""
Bronze ingestion using PySpark DataFrames (Databricks-native).

This version does not rely on databricks-sql-connector or external tokens.
It uses Spark to write synthetic data directly to Delta tables in the
atelier.bronze schema.
"""

import random
from datetime import datetime, timedelta

from pyspark.sql import Row
from pyspark.sql.functions import current_timestamp, lit, uuid

# --- Configuración ---
CATALOG = "atelier"
BRONZE_SCHEMA = "bronze"

# --- Funciones auxiliares ---
def write_batch(df, table_name, run_id, spark_session):
    """Escribe el DataFrame en la tabla Bronze, añadiendo metadatos de ingesta."""
    full_name = f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}"
    df_with_meta = df.withColumn("ingestion_run_id", lit(run_id)) \
                     .withColumn("ingested_at", current_timestamp())
    df_with_meta.write.format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .saveAsTable(full_name)

# --- 1. Generar datos sintéticos de tendencias ---
def generate_trend_signals(spark_session, n=100):
    sources = ["WGSN", "Vogue Runway", "Pantone", "Trendstop", "Instagram"]
    seasons = ["Spring/Summer", "Fall/Winter", "Pre-Fall", "Resort"]
    colours = ["Pastel", "Neon", "Earth tones", "Monochrome", "Metallic"]
    silhouettes = ["Oversize", "Tailored", "Flowing", "Boxy", "Asymmetric"]
    regions = ["Global", "Europe", "Americas", "Asia"]
    rows = []
    for i in range(n):
        rows.append(Row(
            signal_id=f"TR-{i:04d}",
            source=random.choice(sources),
            season=random.choice(seasons),
            colour=random.choice(colours),
            silhouette=random.choice(silhouettes),
            captured_at=(datetime.now() - timedelta(days=random.randint(0, 180))).isoformat(),
            payload=(
                f'{{"confidence": {round(random.uniform(0.6, 0.95), 2)}, '
                f'"region": "{random.choice(regions)}"}}'
            )
        ))
    return spark_session.createDataFrame(rows)

# --- 2. Generar datos sintéticos de inventario ---
def generate_inventory(spark_session, n=200):
    warehouses = ["MAD", "BCN", "LIS", "PAR", "NYC", "LON", "MIL"]
    rows = []
    for i in range(n):
        rows.append(Row(
            sku=f"SKU-{i:05d}",
            warehouse=random.choice(warehouses),
            quantity_on_hand=str(random.randint(0, 500)),
            as_of_date=(datetime.now() - timedelta(days=random.randint(0, 30))).date().isoformat(),
            payload=f'{{"batch": "B{random.randint(2024, 2026)}-{random.randint(1, 12):02d}"}}'
        ))
    return spark_session.createDataFrame(rows)

# --- 3. Generar datos sintéticos de ventas ---
def generate_sales_history(spark_session, n=300):
    markets = ["ES", "FR", "IT", "DE", "UK", "US", "JP", "BR"]
    channels = ["online", "retail", "pop-up"]
    rows = []
    for i in range(n):
        rows.append(Row(
            order_id=f"ORD-{i:06d}",
            sku=f"SKU-{random.randint(0, 199):05d}",
            market=random.choice(markets),
            units_sold=str(random.randint(1, 50)),
            sale_date=(datetime.now() - timedelta(days=random.randint(0, 365))).date().isoformat(),
            payload=f'{{"channel": "{random.choice(channels)}"}}'
        ))
    return spark_session.createDataFrame(rows)

# --- 4. Generar datos sintéticos de clima ---
def generate_climate(spark_session):
    regions = ["North", "South", "East", "West"]
    seasons = ["Spring", "Summer", "Fall", "Winter"]
    rows = []
    for region in regions:
        for season in seasons:
            rows.append(Row(
                region=region,
                season=season,
                avg_temp_c=str(round(random.uniform(5, 30), 1)),
                avg_rainfall_mm=str(round(random.uniform(10, 200), 1)),
                captured_at=datetime.now().isoformat()
            ))
    return spark_session.createDataFrame(rows)

# --- 5. Generar datos sintéticos de social listening ---
def generate_social_listening(spark_session, n=150):
    platforms = ["Instagram", "TikTok", "Pinterest", "YouTube", "X"]
    hashtags = ["#fashion", "#style", "#trend", "#ootd"]
    languages = ["en", "es", "fr", "it"]
    rows = []
    for i in range(n):
        rows.append(Row(
            post_id=f"POST-{i:06d}",
            platform=random.choice(platforms),
            captured_at=(datetime.now() - timedelta(hours=random.randint(1, 720))).isoformat(),
            sentiment_score=str(round(random.uniform(-1, 1), 2)),
            payload=(
                f'{{"hashtags": ["{random.choice(hashtags)}"], '
                f'"language": "{random.choice(languages)}"}}'
            )
        ))
    return spark_session.createDataFrame(rows)

# --- Ejecución principal ---
if __name__ == "__main__":
    # `spark` está disponible en el entorno de Databricks,
    # pero lo pasamos explícitamente a las funciones para
    # que el script sea autocontenido y testeable.
    # En Databricks, simplemente usamos la variable global `spark`.
    try:
        spark_session = spark
    except NameError:
        raise RuntimeError(
            "Este script debe ejecutarse en un entorno con una sesión Spark activa "
            "(por ejemplo, en un notebook de Databricks)."
        )

    # Generar un UUID para esta ejecución
    run_id = str(uuid().alias("dummy")).split("'")[1]  # Truco para obtener UUID

    # Diccionario con el nombre de la tabla y la función generadora
    tables = [
        ("trend_signals_raw", generate_trend_signals),
        ("inventory_raw", generate_inventory),
        ("sales_history_raw", generate_sales_history),
        ("climate_raw", generate_climate),
        ("social_listening_raw", generate_social_listening),
    ]

    for table_name, generator_func in tables:
        print(f"Ingesting {table_name}...")
        df = generator_func(spark_session)
        write_batch(df, table_name, run_id, spark_session)

    print("Ingestión completada.")
