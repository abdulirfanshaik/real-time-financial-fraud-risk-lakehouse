"""Reference Spark Structured Streaming job for Databricks or Spark clusters.

The local demo in src/risk_lakehouse is dependency-free. This job shows the
production-oriented Kafka to Delta implementation described in the architecture.
"""

from pyspark.sql import SparkSession, functions as F, types as T


KAFKA_SERVERS = "${KAFKA_BOOTSTRAP_SERVERS}"
TOPIC = "financial.card_authorizations.v1"
CHECKPOINT_ROOT = "s3://replace-me/checkpoints/fraud-risk"
DELTA_ROOT = "s3://replace-me/lakehouse/fraud-risk"

schema = T.StructType(
    [
        T.StructField("event_id", T.StringType(), False),
        T.StructField("transaction_id", T.StringType(), False),
        T.StructField("customer_id", T.StringType(), False),
        T.StructField("account_id", T.StringType(), False),
        T.StructField("card_id", T.StringType(), False),
        T.StructField("event_ts", T.StringType(), False),
        T.StructField("ingest_ts", T.StringType(), False),
        T.StructField("amount", T.DoubleType(), False),
        T.StructField("currency", T.StringType(), False),
        T.StructField("merchant_id", T.StringType(), False),
        T.StructField("merchant_category", T.StringType(), False),
        T.StructField("merchant_country", T.StringType(), False),
        T.StructField("customer_country", T.StringType(), False),
        T.StructField("device_id", T.StringType(), False),
        T.StructField("channel", T.StringType(), False),
        T.StructField("decision", T.StringType(), False),
        T.StructField("source_system", T.StringType(), False),
    ]
)


def build_stream(spark: SparkSession):
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_SERVERS)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "true")
        .load()
    )

    bronze = raw.select(
        F.col("key").cast("string").alias("message_key"),
        F.col("value").cast("string").alias("raw_payload"),
        F.col("topic"),
        F.col("partition"),
        F.col("offset"),
        F.col("timestamp").alias("kafka_timestamp"),
    )

    silver = (
        bronze.select(F.from_json("raw_payload", schema).alias("event"), "*")
        .select("event.*", "topic", "partition", "offset", "kafka_timestamp")
        .withColumn("event_timestamp", F.to_timestamp("event_ts"))
        .filter(F.col("amount") > 0)
        .filter(F.col("event_id").isNotNull())
        .withWatermark("event_timestamp", "30 minutes")
        .dropDuplicates(["source_system", "event_id"])
    )

    scored = (
        silver.withColumn(
            "risk_score",
            F.when(F.col("amount") >= 2000, 35).otherwise(0)
            + F.when(F.col("merchant_category").isin("CRYPTO", "GAMBLING"), 25).otherwise(0)
            + F.when(F.col("merchant_country") != F.col("customer_country"), 15).otherwise(0)
            + F.when(F.col("decision") == "DECLINED", 10).otherwise(0),
        )
        .withColumn(
            "alert_severity",
            F.when(F.col("risk_score") >= 80, "HIGH")
            .when(F.col("risk_score") >= 60, "MEDIUM")
            .otherwise("NONE"),
        )
    )
    return bronze, silver, scored


def start_query(frame, name: str, path: str):
    return (
        frame.writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINT_ROOT}/{name}")
        .option("path", path)
        .queryName(name)
        .start()
    )


if __name__ == "__main__":
    spark = SparkSession.builder.appName("financial-fraud-risk-lakehouse").getOrCreate()
    bronze_df, silver_df, scored_df = build_stream(spark)
    queries = [
        start_query(bronze_df, "bronze_card_authorizations", f"{DELTA_ROOT}/bronze/card_authorizations"),
        start_query(silver_df, "silver_card_transactions", f"{DELTA_ROOT}/silver/card_transactions"),
        start_query(
            scored_df.filter("alert_severity <> 'NONE'"),
            "gold_fraud_alerts",
            f"{DELTA_ROOT}/gold/fraud_alerts",
        ),
    ]
    for query in queries:
        query.awaitTermination()

