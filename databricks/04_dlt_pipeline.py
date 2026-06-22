"""
Delta Live Tables pipeline definition wiring Bronze, Silver and Gold into a
single declarative pipeline, so that batch sources (sales, inventory) and
the faster-moving streaming source (social listening) are scheduled and
monitored together rather than as separate, hand-rolled jobs.

This file is uploaded as a DLT pipeline notebook in the Databricks
workspace, not run directly with python.
"""

import dlt
from pyspark.sql.functions import current_timestamp


@dlt.table(name="trend_signals_bronze", comment="Raw trend signals, append only")
def trend_signals_bronze():
    return spark.readStream.format("cloudFiles").option("cloudFiles.format", "json").load(
        "/Volumes/atelier/landing/trend_signals/"
    )


@dlt.table(name="social_listening_bronze", comment="Streaming social listening signals")
def social_listening_bronze():
    return spark.readStream.format("cloudFiles").option("cloudFiles.format", "json").load(
        "/Volumes/atelier/landing/social_listening/"
    )


@dlt.table(name="trend_signals_silver", comment="Validated trend signals")
@dlt.expect_or_drop("has_season", "season IS NOT NULL")
@dlt.expect_or_drop("has_colour", "colour IS NOT NULL")
def trend_signals_silver():
    return dlt.read_stream("trend_signals_bronze").select(
        "signal_id", "source", "season", "colour", "silhouette", "captured_at"
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
