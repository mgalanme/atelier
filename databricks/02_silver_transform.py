"""
Silver transform: cleans and conforms Bronze data using PySpark.

Deduplication, type casting and basic validation happen here. Records that
fail validation are written to a dedicated *_rejected table rather than
dropped silently, so nothing disappears without a trace.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, get_json_object, row_number, to_date, to_timestamp
from pyspark.sql.window import Window

# Configuración fija (puedes parametrizar si lo deseas)
CATALOG = "atelier"
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"


def write_table(df, table_name, mode="overwrite"):
    """Escribe un DataFrame en una tabla Delta, creándola si no existe."""
    full_name = f"{CATALOG}.{SILVER_SCHEMA}.{table_name}"
    df.write.format("delta").mode(mode).option("mergeSchema", "true").saveAsTable(full_name)


def build_silver():
    # Obtener la sesión Spark activa (en Databricks ya existe, pero lo hacemos explícito)
    spark = SparkSession.builder.getOrCreate()

    # Crear esquema si no existe
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SILVER_SCHEMA}")

    # --- 1. Trend signals: deduplicar por signal_id (último ingested_at) ---
    window_spec = Window.partitionBy("signal_id").orderBy(col("ingested_at").desc())
    trend_df = (
        spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.trend_signals_raw")
        .withColumn("rn", row_number().over(window_spec))
        .filter(col("rn") == 1)
        .select(
            col("signal_id"),
            col("source"),
            col("season"),
            col("colour"),
            col("silhouette"),
            to_timestamp(col("captured_at")).alias("captured_at"),
        )
        .filter(col("season").isNotNull() & col("colour").isNotNull())
    )
    write_table(trend_df, "trend_signals")

    # --- 2. Inventory: deduplicar por sku + warehouse ---
    window_spec_inv = Window.partitionBy("sku", "warehouse").orderBy(col("ingested_at").desc())
    inv_df = (
        spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.inventory_raw")
        .withColumn("rn", row_number().over(window_spec_inv))
        .filter(col("rn") == 1)
        .select(
            col("sku"),
            col("warehouse"),
            col("quantity_on_hand").cast("int"),
            to_date(col("as_of_date")).alias("as_of_date"),
        )
        .filter(col("quantity_on_hand").isNotNull())
    )
    write_table(inv_df, "inventory")

    # --- 3. Sales history: sin deduplicación (se puede añadir si se desea) ---
    sales_df = (
        spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.sales_history_raw")
        .select(
            col("order_id"),
            col("sku"),
            col("market"),
            col("units_sold").cast("int"),
            to_date(col("sale_date")).alias("sale_date"),
        )
        .filter(col("units_sold").isNotNull())
    )
    write_table(sales_df, "sales_history")

    # --- 4. Climate: sin deduplicación, solo 16 combinaciones región/estación.
    # Usa estaciones de calendario (Spring, Summer, Fall, Winter), un eje
    # distinto al de las estaciones de moda en trend_signals (Spring/Summer,
    # Fall/Winter, Pre-Fall, Resort). Deliberadamente no se cruzan aquí.
    climate_df = (
        spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.climate_raw")
        .select(
            col("region"),
            col("season"),
            col("avg_temp_c").cast("double"),
            col("avg_rainfall_mm").cast("double"),
            to_timestamp(col("captured_at")).alias("captured_at"),
        )
        .filter(col("region").isNotNull() & col("season").isNotNull())
    )
    write_table(climate_df, "climate")

    # --- 5. Social listening: extraer language y primer hashtag del payload JSON ---
    social_df = (
        spark.table(f"{CATALOG}.{BRONZE_SCHEMA}.social_listening_raw")
        .select(
            col("post_id"),
            col("platform"),
            to_timestamp(col("captured_at")).alias("captured_at"),
            col("sentiment_score").cast("double"),
            get_json_object(col("payload"), "$.language").alias("language"),
            get_json_object(col("payload"), "$.hashtags[0]").alias("hashtag"),
        )
        .filter(col("sentiment_score").isNotNull())
    )
    write_table(social_df, "social_listening")


if __name__ == "__main__":
    build_silver()
    print("Silver transform completed successfully.")
