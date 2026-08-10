"""
pipeline/load_bronze.py
-------------------------
Etape 2 : charge les evenements bruts (JSON) dans evenements_bronze.
Deduplication sur (uid, updated_at_source) : un evenement inchange
depuis le dernier import n'est pas re-insere ; une vraie mise a jour
source cree une nouvelle ligne (historique Bronze preserve).
"""

import json
from backend.database import get_connection
from config import PIPELINE_RAW_JSON


def load_bronze():
    with open(PIPELINE_RAW_JSON, "r", encoding="utf-8") as f:
        events = json.load(f)

    conn = get_connection()
    inserted = 0
    skipped = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for event in events:
                    cur.execute(
                        """
                        INSERT INTO evenements_bronze (uid, raw_data, updated_at_source)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (uid, updated_at_source) DO NOTHING
                        """,
                        (event["uid"], json.dumps(event, ensure_ascii=False), event.get("updatedat")),
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
    finally:
        conn.close()

    print(f"{inserted} evenements inseres dans evenements_bronze.")
    print(f"{skipped} evenements deja connus (meme uid + meme updatedat), ignores.")


if __name__ == "__main__":
    load_bronze()