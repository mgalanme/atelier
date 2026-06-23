"""
Gold curation: builds the business-ready entities (Collection, Garment,
Material, Trend, Decision) that every agent and predictive model reads from.

LESSON LEARNED (reused from earlier case studies): MERGE INTO with INSERT *
fails once a prior session has contaminated the DataFrame schema with extra
or reordered columns. Every MERGE below uses an explicit column list on both
the INSERT and UPDATE clauses, never INSERT * or UPDATE SET *.
"""

from pyspark.sql import SparkSession

# Configuración fija (puedes parametrizar si lo deseas)
CATALOG = "atelier"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"

# Explicit column list for trends, kept as a constant so every MERGE statement
# that touches this table uses exactly the same columns in the same order.
TREND_COLS = ["trend_id", "season", "colour", "silhouette", "signal_count", "last_seen_at"]


def get_spark():
    """Obtiene la sesión Spark activa (en Databricks ya existe)."""
    return SparkSession.builder.getOrCreate()


def build_gold():
    spark = get_spark()

    # Crear esquema si no existe
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}")

    # --- 1. Crear tablas (si no existen) ---
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

    # --- 2. Recalcular trends como snapshot completo ---
    # Bronze y Silver ahora se sobrescriben en cada ejecución (overwrite,
    # no append), así que Gold sigue la misma semántica de snapshot: un
    # INSERT OVERWRITE, no un MERGE acumulativo. decisions es la excepción
    # deliberada (ver record_decision más abajo): es un registro de
    # auditoría de eventos HITL reales, no un dato sintético recalculable.
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

    # --- 3. Generar documentos de texto para Vector Search ---
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
