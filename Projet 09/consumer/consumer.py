import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, count, window, when
)
from pyspark.sql.types import StructType, StructField, StringType

# ── Configuration ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = os.environ.get("BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC             = "client_tickets"
OUTPUT_DIR        = "./output"
CHECKPOINT_DIR    = "./checkpoint"

# ── Schéma des tickets ─────────────────────────────────────────────────────────
TICKET_SCHEMA = StructType([
    StructField("ticket_id",    StringType(), True),
    StructField("client_id",    StringType(), True),
    StructField("created_at",   StringType(), True),
    StructField("request_type", StringType(), True),
    StructField("request",      StringType(), True),
    StructField("priority",     StringType(), True),
])

# ── Mapping type de demande → équipe support ───────────────────────────────────
def assign_support_team(df):
    return df.withColumn(
        "support_team",
        when(col("request_type") == "Facturation",        "Équipe Facturation")
        .when(col("request_type") == "Support technique", "Équipe Technique")
        .when(col("request_type") == "Retour produit",    "Équipe Logistique")
        .when(col("request_type") == "Livraison",         "Équipe Livraison")
        .when(col("request_type") == "Information",       "Équipe Relation Client")
        .otherwise("Équipe Générale")
    )


def main():
    # ── Création de la SparkSession ────────────────────────────────────────────
    spark = (
        SparkSession.builder
        .appName("InduTech - Tickets Client")
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.1")
        # Mémoire : adapté pour un poste local
        .config("spark.driver.memory",   "2g")
        .config("spark.executor.memory", "2g")
        # Partitions : aligné sur nos 3 partitions Kafka
        .config("spark.sql.shuffle.partitions", "3")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print("✅ SparkSession démarrée")

    # ── Lecture du stream Kafka ────────────────────────────────────────────────
    raw_stream = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", BOOTSTRAP_SERVERS)
        .option("subscribe",               TOPIC)
        .option("startingOffsets",         "earliest")
        # Résilience : si Kafka est temporairement indisponible, on réessaie
        .option("failOnDataLoss",          "false")
        .load()
    )

    # ── Désérialisation JSON ───────────────────────────────────────────────────
    tickets = (
        raw_stream
        .select(from_json(col("value").cast("string"), TICKET_SCHEMA).alias("data"))
        .select("data.*")
        .withColumn("created_at", to_timestamp(col("created_at")))
    )

    # ── Transformation : ajout équipe support ─────────────────────────────────
    tickets_enriched = assign_support_team(tickets)

    # ── Agrégation 1 : nombre de tickets par type ──────────────────────────────
    tickets_by_type = (
        tickets_enriched
        .groupBy("request_type", "support_team")
        .agg(count("*").alias("nb_tickets"))
    )

    # ── Agrégation 2 : nombre de tickets par priorité ─────────────────────────
    tickets_by_priority = (
        tickets_enriched
        .groupBy("priority")
        .agg(count("*").alias("nb_tickets"))
    )

    # ── Écriture 1 : tickets enrichis bruts → JSON ────────────────────────────
    os.makedirs(OUTPUT_DIR,    exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    query_raw = (
        tickets_enriched.writeStream
        .outputMode("append")
        .format("json")
        .option("path",            f"{OUTPUT_DIR}/tickets_enriched")
        .option("checkpointLocation", f"{CHECKPOINT_DIR}/raw")
        .trigger(processingTime="10 seconds")
        .start()
    )

    # ── Écriture 2 : agrégation par type → console (debug) ────────────────────
    query_by_type = (
        tickets_by_type.writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", False)
        .trigger(processingTime="10 seconds")
        .start()
    )

    # ── Écriture 3 : agrégation par priorité → console (debug) ────────────────
    query_by_priority = (
        tickets_by_priority.writeStream
        .outputMode("complete")
        .format("console")
        .option("truncate", False)
        .trigger(processingTime="10 seconds")
        .start()
    )

    print("📡 Pipeline en écoute sur Redpanda... (Ctrl+C pour arrêter)\n")

    # Attente de toutes les queries
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()