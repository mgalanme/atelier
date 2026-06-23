"""
Gold curation: builds the business-ready entities (Collection, Garment,
Material, Trend, Decision) that every agent and predictive model reads from.

NOTE: Bronze and Silver now overwrite on every run (a full synthetic
snapshot, not an accumulating history), so trends here uses a plain
INSERT OVERWRITE rather than a MERGE. decisions remains a pure INSERT: it
is an audit log of real Human-in-the-Loop events, not a refreshable
snapshot, and must persist across runs.

climate_profile and social_sentiment follow the same snapshot semantics as
trends: a full INSERT OVERWRITE on every run, since their Silver sources
are themselves full snapshots, not accumulating history.
"""

from pyspark.sql import SparkSession

# Configuración fija (puedes parametrizar si lo deseas)
CATALOG = "atelier"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"


def get_spark():
    """Obtiene la sesión Spark activa (en Databricks ya existe)."""
    return SparkSession.builder.getOrCreate()


def build_gold():
    spark = get_spark()

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}")

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.trends (
            trend_id STRING, season STRING, colour STRING, silhouette STRING,
            signal_count INT, last_seen_at TIMESTAMP
        )
    """)

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.decisions (
            decision_id STRING, collection_id STRING, persona STRING,
            decision_type STRING, comment STRING, decided_at TIMESTAMP
        )
    """)

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.trend_documents (
            document_id STRING, document_text STRING, season STRING, refreshed_at TIMESTAMP
        )
    """)

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.climate_profile (
            region STRING, season STRING, avg_temp_c DOUBLE, avg_rainfall_mm DOUBLE,
            climate_band STRING, refreshed_at TIMESTAMP
        )
    """)

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.social_sentiment (
            platform STRING, hashtag STRING, language STRING,
            post_count INT, avg_sentiment DOUBLE, refreshed_at TIMESTAMP
        )
    """)

    # --- Recalcular trends como snapshot completo (no MERGE) ---
    spark.sql(f"""
        INSERT OVERWRITE TABLE {CATALOG}.{GOLD_SCHEMA}.trends
        SELECT
            concat(season, '-', colour, '-', coalesce(silhouette, 'na')) AS trend_id,
            season, colour, silhouette,
            count(*) AS signal_count,
            max(captured_at) AS last_seen_at
        FROM {CATALOG}.{SILVER_SCHEMA}.trend_signals
        GROUP BY season, colour, silhouette
    """)

    # --- Generar documentos de texto para Vector Search ---
    spark.sql(f"""
        INSERT OVERWRITE TABLE {CATALOG}.{GOLD_SCHEMA}.trend_documents
        SELECT
            trend_id AS document_id,
            concat('Season: ', season, '. Colour: ', colour,
                   '. Silhouette: ', coalesce(silhouette, 'unspecified'),
                   '. Observed in ', cast(signal_count AS STRING), ' signals.') AS document_text,
            season,
            current_timestamp() AS refreshed_at
        FROM {CATALOG}.{GOLD_SCHEMA}.trends
    """)

    # --- Climate profile: una fila por región/estación de calendario, con
    # una banda de clima derivada para que sea legible sin tener que
    # interpretar la temperatura cruda. ---
    spark.sql(f"""
        INSERT OVERWRITE TABLE {CATALOG}.{GOLD_SCHEMA}.climate_profile
        SELECT
            region, season, avg_temp_c, avg_rainfall_mm,
            CASE
                WHEN avg_temp_c < 10 THEN 'Cold'
                WHEN avg_temp_c < 18 THEN 'Mild'
                WHEN avg_temp_c < 26 THEN 'Warm'
                ELSE 'Hot'
            END AS climate_band,
            current_timestamp() AS refreshed_at
        FROM {CATALOG}.{SILVER_SCHEMA}.climate
    """)

    # --- Social sentiment: agregado por plataforma, hashtag e idioma,
    # mismo patrón que trends (de eventos individuales a resumen). ---
    spark.sql(f"""
        INSERT OVERWRITE TABLE {CATALOG}.{GOLD_SCHEMA}.social_sentiment
        SELECT
            platform, hashtag, language,
            count(*) AS post_count,
            avg(sentiment_score) AS avg_sentiment,
            current_timestamp() AS refreshed_at
        FROM {CATALOG}.{SILVER_SCHEMA}.social_listening
        GROUP BY platform, hashtag, language
    """)


def record_decision(
    decision_id: str, collection_id: str, persona: str, decision_type: str, comment: str
):
    """
    Sanitises free-text fields before they reach a SQL statement, since
    `comment` may originate from an LLM-generated narrative rather than a
    fixed UI choice. Single quotes are escaped, newlines and carriage
    returns are flattened to spaces, null bytes are stripped, and the value
    is truncated to a safe length.
    """
    spark = get_spark()
    safe_comment = (
        comment.replace("\x00", "").replace("\r", " ").replace("\n", " ").replace("'", "''")
    )[:2000]

    spark.sql(f"""
        INSERT INTO {CATALOG}.{GOLD_SCHEMA}.decisions
        (decision_id, collection_id, persona, decision_type, comment, decided_at)
        VALUES ('{decision_id}', '{collection_id}', '{persona}', '{decision_type}',
                '{safe_comment}', current_timestamp())
    """)


if __name__ == "__main__":
    build_gold()
    print("Gold curation completed successfully.")
