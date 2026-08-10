"""
pipeline/transform_gold.py
-----------------------------
Etape 3 : lit les evenements bruts non traites, applique les regles de
nettoyage (meme esprit que fetch_events.py::clean_events), sauvegarde
en JSON pret pour la couche Gold.
"""

import json
import os
from backend.database import get_connection, get_dict_cursor
from config import PIPELINE_GOLD_JSON

CHAMPS_GARDES = [
    "uid", "title_fr", "description_fr", "longdescription_fr",
    "firstdate_begin", "lastdate_end", "location_name",
    "location_city", "location_department", "location_region",
    "location_address", "conditions_fr", "keywords_fr", "updatedat",
]


def transform():
    conn = get_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT id, raw_data FROM evenements_bronze WHERE processed = FALSE")
            rows = cur.fetchall()
    finally:
        conn.close()

    print(f"{len(rows)} evenements bruts a transformer.")

    gold_events = []
    ids_traites = []

    for row in rows:
        raw = row["raw_data"]
        ids_traites.append(row["id"])

        if not raw.get("title_fr") or not raw.get("description_fr"):
            print(f"  Evenement {raw.get('uid')} ecarte (titre ou description manquant).")
            continue
        if not raw.get("location_city"):
            print(f"  Evenement {raw.get('uid')} ecarte (ville manquante).")
            continue

        gold_events.append({champ: raw.get(champ) for champ in CHAMPS_GARDES})

    os.makedirs(os.path.dirname(PIPELINE_GOLD_JSON), exist_ok=True)
    with open(PIPELINE_GOLD_JSON, "w", encoding="utf-8") as f:
        json.dump({"gold_events": gold_events, "bronze_ids_traites": ids_traites}, f, ensure_ascii=False, indent=2)

    print(f"{len(gold_events)} evenements valides pour la couche Gold.")


if __name__ == "__main__":
    transform()