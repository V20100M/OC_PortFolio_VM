"""
etl_strava.py
-------------
Transformation des données brutes Strava vers les tables métier.

Lit les enregistrements non traités de strava_raw (processed = FALSE),
applique la couche ETL (parsing + validation) et insère les données
transformées dans les tables :
  - strava        (activités)
  - stravathlete  (correspondance activité / athlete)
  - strava_comment (commentaires)

Marque chaque ligne comme traitée (processed = TRUE) après insertion
réussie, ce qui permet de rejouer l'ETL en cas d'erreur partielle
sans dupliquer les données déjà insérées.

Flux :
  strava_raw (processed = FALSE)
  strava_comment_raw (processed = FALSE, même id_strava)
  - parse_activity_and_comments()  (couche ETL partagée)
  - insert_parsed_activity()       (insertion tables)
  - UPDATE strava_raw SET processed = TRUE
  - UPDATE strava_comment_raw SET processed = TRUE

Usage :
  python -m scripts.etl_strava

Prérequis :
  - generate_strava_raw.py doit avoir été exécuté avec succès
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging

from utils.config import BASE_DIR
from utils.strava_etl import parse_activity_and_comments, insert_parsed_activity
from utils.logging_utils import setup_logging
from utils.db import get_connection

setup_logging("etl_strava.log", BASE_DIR)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lecture des données brutes
# ---------------------------------------------------------------------------
def fetch_unprocessed_activities(conn, batch_size=500):
    """
    Récupère les activités non traitées depuis strava_raw.

    Returns:
        Liste de tuples (id, id_strava, raw_activity).
    """
    sql = """
        SELECT id, id_strava, raw_activity
        FROM strava_raw
        WHERE processed = FALSE
        ORDER BY inserted_at ASC
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (batch_size,))
        return cur.fetchall()


def fetch_raw_comments(conn, id_strava):
    """
    Récupère les commentaires bruts non traités pour une activité donnée.

    Returns:
        Liste de tuples (id, raw_comment).
    """
    sql = """
        SELECT id, raw_comment
        FROM strava_comment_raw
        WHERE id_strava = %s
          AND processed = FALSE
        ORDER BY inserted_at ASC;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (id_strava,))
        return cur.fetchall()


def mark_activity_processed(conn, raw_id):
    """Marque une activité dans strava_raw comme traitée."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE strava_raw SET processed = TRUE WHERE id = %s;",
            (raw_id,)
        )


def mark_comments_processed(conn, comment_raw_ids):
    """Marque une liste de commentaires dans strava_comment_raw comme traités."""
    if not comment_raw_ids:
        return
    with conn.cursor() as cur:
        cur.executemany(
            "UPDATE strava_comment_raw SET processed = TRUE WHERE id = %s;",
            [(cid,) for cid in comment_raw_ids]
        )


# ---------------------------------------------------------------------------
# ETL principal
# ---------------------------------------------------------------------------
def run_etl(conn):
    """
    Traite tous les enregistrements non traités de strava_raw par batch.

    Pour chaque activité :
      1. Désérialise le JSON d'activité brut
      2. Récupère et désérialise les commentaires bruts associés
      3. Applique la couche ETL (parse_activity_and_comments)
      4. Insère dans les tables (insert_parsed_activity)
      5. Marque l'activité et ses commentaires comme traités

    En cas d'erreur sur une ligne, celle-ci n'est pas marquée comme traitée
    et sera retraitée au prochain appel, les autres lignes continuent.

    Returns:
        (total_success, total_errors)
    """
    total_success = total_errors = 0
    batch_num     = 0

    while True:
        rows = fetch_unprocessed_activities(conn, batch_size=500)
        if not rows:
            break   # plus rien à traiter

        batch_num += 1
        logger.info("Batch %d : %d enregistrements à transformer", batch_num, len(rows))

        for raw_id, id_strava, raw_activity in rows:
            try:
                # Désérialisation du JSON d'activité
                activity_json = raw_activity if isinstance(raw_activity, dict) else json.loads(raw_activity)

                # Récupération et désérialisation des commentaires bruts associés
                comment_rows = fetch_raw_comments(conn, id_strava)
                comment_raw_ids = [row[0] for row in comment_rows]
                comments_json = [
                    row[1] if isinstance(row[1], dict) else json.loads(row[1])
                    for row in comment_rows
                ]

                # Parsing ETL — identique qu'en production avec la vraie API
                activity_data, comments_data = parse_activity_and_comments(
                    activity_json, comments_json
                )

                # Insertion dans les tables
                insert_parsed_activity(conn, activity_data, comments_data)

                # Marquage comme traité (activité + commentaires)
                mark_activity_processed(conn, raw_id)
                mark_comments_processed(conn, comment_raw_ids)
                conn.commit()
                total_success += 1

            except Exception as exc:
                logger.error(
                    "Erreur ETL id=%s (id_strava=%s) : %s — ligne ignorée, sera retraitée",
                    raw_id, id_strava, exc
                )
                conn.rollback()
                total_errors += 1

    return total_success, total_errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=== Démarrage ETL Strava ===")

    try:
        conn = get_connection()
        logger.info("Connexion PostgreSQL établie")
    except Exception as exc:
        logger.critical("Impossible de se connecter à PostgreSQL : %s", exc)
        return

    try:
        total_success, total_errors = run_etl(conn)
        logger.info(
            "=== ETL terminé : %d activités insérées, %d erreurs ===",
            total_success, total_errors
        )

    except Exception as exc:
        logger.error("Erreur inattendue : %s", exc)
        conn.rollback()
    finally:
        conn.close()
        logger.info("Connexion PostgreSQL fermée.")


if __name__ == "__main__":
    main()