"""
pipeline/load_gold.py
------------------------
Etape 4 : charge les evenements transformes dans evenements_gold, et
marque les lignes Bronze correspondantes comme traitees.
"""

import json
from backend.database import get_connection
from config import PIPELINE_GOLD_JSON


def load_gold():
    with open(PIPELINE_GOLD_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    gold_events = data["gold_events"]
    bronze_ids_traites = data["bronze_ids_traites"]

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                for event in gold_events:
                    cur.execute(
                        """
                        INSERT INTO evenements_gold (
                            uid, title_fr, description_fr, longdescription_fr,
                            firstdate_begin, lastdate_end, location_name,
                            location_city, location_department, location_region,
                            location_address, conditions_fr, keywords_fr, updated_at_source
                        )
                        VALUES (%(uid)s, %(title_fr)s, %(description_fr)s, %(longdescription_fr)s,
                                %(firstdate_begin)s, %(lastdate_end)s, %(location_name)s,
                                %(location_city)s, %(location_department)s, %(location_region)s,
                                %(location_address)s, %(conditions_fr)s, %(keywords_fr)s, %(updatedat)s)
                        ON CONFLICT (uid) DO UPDATE SET
                            title_fr = EXCLUDED.title_fr,
                            description_fr = EXCLUDED.description_fr,
                            longdescription_fr = EXCLUDED.longdescription_fr,
                            firstdate_begin = EXCLUDED.firstdate_begin,
                            lastdate_end = EXCLUDED.lastdate_end,
                            location_city = EXCLUDED.location_city,
                            location_department = EXCLUDED.location_department,
                            location_region = EXCLUDED.location_region,
                            updated_at_source = EXCLUDED.updated_at_source,
                            transformed_at = now(),
                            sent_to_qdrant = FALSE
                        """,
                        event,
                    )

                if bronze_ids_traites:
                    cur.execute(
                        "UPDATE evenements_bronze SET processed = TRUE WHERE id = ANY(%s)",
                        (bronze_ids_traites,),
                    )
    finally:
        conn.close()

    print(f"{len(gold_events)} evenements charges/mis a jour dans evenements_gold.")


if __name__ == "__main__":
    load_gold()