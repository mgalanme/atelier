"""
Gold curation: builds the business-ready entities (Collection, Garment,
Material, Trend, Decision) that every agent and predictive model reads from.

LESSON LEARNED (reused from earlier case studies): MERGE INTO with INSERT *
fails once a prior session has contaminated the DataFrame schema with extra
or reordered columns. Every MERGE below uses an explicit column list on both
the INSERT and UPDATE clauses, never INSERT * or UPDATE SET *.
"""

import os

from databricks import sql
from dotenv import load_dotenv

load_dotenv()

CATALOG = os.environ["ATELIER_CATALOG"]
SILVER_SCHEMA = os.environ["ATELIER_SCHEMA_SILVER"]
GOLD_SCHEMA = os.environ["ATELIER_SCHEMA_GOLD"]

# Explicit column list, kept as a constant so every MERGE statement that
# touches this table uses exactly the same columns in exactly the same order.
TREND_COLS = ["trend_id", "season", "colour", "silhouette", "signal_count", "last_seen_at"]


def get_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def build_gold(cursor):
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.trends (
            trend_id STRING, season STRING, colour STRING, silhouette STRING,
            signal_count INT, last_seen_at TIMESTAMP
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.decisions (
            decision_id STRING, collection_id STRING, persona STRING,
            decision_type STRING, comment STRING, decided_at TIMESTAMP
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{GOLD_SCHEMA}.trend_documents (
            document_id STRING, document_text STRING, season STRING, refreshed_at TIMESTAMP
        )
    """)

    insert_cols = ", ".join(TREND_COLS)
    update_assignments = ", ".join(f"target.{c} = source.{c}" for c in TREND_COLS if c != "trend_id")
    source_cols = ", ".join(f"source.{c}" for c in TREND_COLS)

    cursor.execute(f"""
        MERGE INTO {CATALOG}.{GOLD_SCHEMA}.trends AS target
        USING (
            SELECT
                concat(season, '-', colour, '-', coalesce(silhouette, 'na')) AS trend_id,
                season, colour, silhouette,
                count(*) AS signal_count,
                max(captured_at) AS last_seen_at
            FROM {CATALOG}.{SILVER_SCHEMA}.trend_signals
            GROUP BY season, colour, silhouette
        ) AS source
        ON target.trend_id = source.trend_id
        WHEN MATCHED THEN UPDATE SET {update_assignments}
        WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({source_cols})
    """)

    # One natural-language document per trend, used as the source for the
    # Vector Search index created in 05_vector_search_setup.py.
    cursor.execute(f"""
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


def record_decision(cursor, decision_id: str, collection_id: str, persona: str,
                     decision_type: str, comment: str):
    """
    Sanitises free-text fields before they reach a SQL statement, since
    `comment` may originate from an LLM-generated narrative rather than a
    fixed UI choice. Single quotes are escaped, newlines and carriage
    returns are flattened to spaces, null bytes are stripped, and the value
    is truncated to a safe length.
    """
    safe_comment = (
        comment.replace("\x00", "")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("'", "''")
    )[:2000]

    cursor.execute(f"""
        INSERT INTO {CATALOG}.{GOLD_SCHEMA}.decisions
        (decision_id, collection_id, persona, decision_type, comment, decided_at)
        VALUES ('{decision_id}', '{collection_id}', '{persona}', '{decision_type}',
                '{safe_comment}', current_timestamp())
    """)


if __name__ == "__main__":
    connection = get_connection()
    with connection.cursor() as cursor:
        build_gold(cursor)
    connection.close()
