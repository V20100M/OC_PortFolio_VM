import os
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count
from pyspark.sql.types import StructType, StructField, StringType, TimestampType

# ── Configuration ──────────────────────────────────────────────────────────────
INPUT_DIR  = os.environ.get("INPUT_DIR",  "./output/tickets_enriched")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./output/reports")

# ── Schéma des tickets enrichis ────────────────────────────────────────────────
TICKET_SCHEMA = StructType([
    StructField("ticket_id",    StringType(),    True),
    StructField("client_id",    StringType(),    True),
    StructField("created_at",   TimestampType(), True),
    StructField("request_type", StringType(),    True),
    StructField("request",      StringType(),    True),
    StructField("priority",     StringType(),    True),
    StructField("support_team", StringType(),    True),
])


def wait_for_data(path: str, check_interval: int = 15):
    """Attend que le répertoire existe et contienne au moins un fichier JSON."""
    while True:
        if os.path.exists(path):
            files = [f for f in os.listdir(path) if f.endswith(".json")]
            if files:
                print(f"✅ Données disponibles dans {path} ({len(files)} fichier(s))")
                return
            else:
                print(f"⏳ Répertoire {path} existe mais aucun fichier JSON encore...")
        else:
            print(f"⏳ En attente de données dans {path}...")
        time.sleep(check_interval)


def main():
    # ── Attente que le consumer ait écrit des données ──────────────────────────
    wait_for_data(INPUT_DIR)

    # ── SparkSession ───────────────────────────────────────────────────────────
    spark = (
        SparkSession.builder
        .appName("InduTech - Export Reports")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "3")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print("✅ SparkSession démarrée")

    # ── Lecture des tickets enrichis (batch, pas streaming) ────────────────────
    tickets = (
        spark.read
        .schema(TICKET_SCHEMA)
        .json(INPUT_DIR)
    )

    total = tickets.count()
    print(f"📂 {total} tickets chargés depuis {INPUT_DIR}\n")

    if total == 0:
        print("⚠️  Aucun ticket trouvé. Assurez-vous que consumer.py a bien tourné.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Rapport 1 : tickets par type de demande ────────────────────────────────
    report_by_type = (
        tickets
        .groupBy("request_type", "support_team")
        .agg(count("*").alias("nb_tickets"))
        .orderBy(col("nb_tickets").desc())
    )
    report_by_type.show(truncate=False)
    report_by_type.write.mode("overwrite").parquet(f"{OUTPUT_DIR}/by_type")
    print(f"✅ Rapport par type exporté → {OUTPUT_DIR}/by_type")

    # ── Rapport 2 : tickets par priorité ──────────────────────────────────────
    report_by_priority = (
        tickets
        .groupBy("priority")
        .agg(count("*").alias("nb_tickets"))
        .orderBy(col("nb_tickets").desc())
    )
    report_by_priority.show(truncate=False)
    report_by_priority.write.mode("overwrite").parquet(f"{OUTPUT_DIR}/by_priority")
    print(f"✅ Rapport par priorité exporté → {OUTPUT_DIR}/by_priority")

    # ── Rapport 3 : tickets par client (top 10) ────────────────────────────────
    report_by_client = (
        tickets
        .groupBy("client_id")
        .agg(count("*").alias("nb_tickets"))
        .orderBy(col("nb_tickets").desc())
        .limit(10)
    )
    report_by_client.show(truncate=False)
    report_by_client.write.mode("overwrite").parquet(f"{OUTPUT_DIR}/top10_clients")
    print(f"✅ Top 10 clients exporté → {OUTPUT_DIR}/top10_clients")

    # ── Rapport 4 : tickets critiques ─────────────────────────────────────────
    report_critical = (
        tickets
        .filter(col("priority") == "critical")
        .select("ticket_id", "client_id", "created_at",
                "request_type", "support_team", "request")
        .orderBy(col("created_at").desc())
    )
    report_critical.show(truncate=False)
    report_critical.write.mode("overwrite").parquet(f"{OUTPUT_DIR}/critical_tickets")
    print(f"✅ Tickets critiques exportés → {OUTPUT_DIR}/critical_tickets")

    print("\n🎉 Tous les rapports ont été exportés avec succès !")
    spark.stop()


if __name__ == "__main__":
    main()