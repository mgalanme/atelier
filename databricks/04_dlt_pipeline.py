"""
Delta Live Tables pipeline - Adapted for the pilot to read from existing Bronze tables
instead of streaming from Volumes. This still demonstrates DLT orchestration,
expectations, and Medallion flows.
"""
import dlt
from pyspark.sql.functions import current_timestamp


@dlt.table(name="trend_signals_bronze", comment="Raw trend signals (read from existing bronze table)")
def trend_signals_bronze():
    # En lugar de leer de Volumes, leemos de la tabla Bronze que ya tienes
    return spark.sql("SELECT * FROM atelier.bronze.trend_signals_raw")  # noqa: F821


@dlt.table(name="social_listening_bronze", comment="Social listening signals (read from existing bronze table)")
def social_listening_bronze():
    return spark.sql("SELECT * FROM atelier.bronze.social_listening_raw")  # noqa: F821


@dlt.table(name="trend_signals_silver", comment="Validated trend signals")
@dlt.expect_or_drop("has_season", "season IS NOT NULL")
@dlt.expect_or_drop("has_colour", "colour IS NOT NULL")
def trend_signals_silver():
    return (
        dlt.read("trend_signals_bronze")
        .select("signal_id", "source", "season", "colour", "silhouette", "captured_at")
    )


@dlt.table(name="trends_gold", comment="Aggregated trend strength by season, colour and silhouette")
def trends_gold():
    return (
        dlt.read("trend_signals_silver")
        .groupBy("season", "colour", "silhouette")
        .count()
        .withColumnRenamed("count", "signal_count")
        .withColumn("last_refreshed_at", current_timestamp())
    )
