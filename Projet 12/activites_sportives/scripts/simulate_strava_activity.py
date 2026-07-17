"""
simulate_strava_activity.py
----------------------------
Simule l'arrivée d'une nouvelle activité Strava en temps réel pour
un salarié sportif tiré au hasard, et l'insère en base PostgreSQL.

Flux ETL (identique à generate_strava_raw.py, mais pour une seule activité) :
  1. simulate_activity_json()       : JSON format DetailedActivity (getActivityById)
  2. simulate_comments_json()       : JSON format Comment[] (getCommentsByActivityId)
  3. INSERT INTO strava_raw         : stockage brut de l'activité
  4. INSERT INTO strava_comment_raw : stockage brut des commentaires si présents


L'insertion déclenche le flux CDC :
  PostgreSQL (WAL) → Debezium → Redpanda → Kestra → consumer_slack.py → Slack


Usage :
  python -m scripts.simulate_strava_activity (appelé par pipeline_live.py, ne pas exécuter seul en production)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import logging
from datetime import datetime, timedelta

from utils.config import STRAVA_ID_MIN, STRAVA_ID_MAX, BASE_DIR
from utils.db import get_connection
from utils.logging_utils import setup_logging
from utils.strava_generation import generate_activity_metrics
from utils.strava_etl import (
    simulate_activity_json,
    simulate_comments_json
)



# ---------------------------------------------------------------------------
# Logging UTF-8 robuste (IDEs, pytest, redirection)
# ---------------------------------------------------------------------------
setup_logging("simulate_strava_activity.log", BASE_DIR)
logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_random_sportif(conn):
    """Retourne (id_athlete, pratique_sport) d'un salarie sportif au hasard.
    Retourne None si aucun salarié sportif n'est trouvé en base.
    """
    sql = """
        SELECT sa.id_athlete, sp.pratique_sport
        FROM salarieathlete sa
        JOIN sportpratique sp ON sa.id_salarie = sp.id_salarie
        ORDER BY random()
        LIMIT 1;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()


def generate_unique_strava_id(conn):
    """Genere un id_strava non present dans la table strava.
    Vérifie en base pour garantir l'unicité même entre sessions.
    """
    with conn.cursor() as cur:
        for _ in range(50):
            id_strava = random.randint(STRAVA_ID_MIN, STRAVA_ID_MAX)
            cur.execute(
                """
                SELECT 1 FROM strava     WHERE id_strava = %s
                UNION ALL
                SELECT 1 FROM strava_raw WHERE id_strava = %s;
                """,
                (id_strava, id_strava)
            )
            if cur.fetchone() is None:
                return id_strava
    raise RuntimeError("Impossible de generer un id_strava unique après 50 tentatives.")


def store_raw_activity(conn, id_strava, activity_json):
    """Insère le JSON d'activité brut dans strava_raw (couche bronze)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO strava_raw (id_strava, raw_activity) VALUES (%s, %s);",
            (id_strava, json.dumps(activity_json)),
        )


def store_raw_comments(conn, id_strava, comments_json):
    """
    Insère chaque commentaire brut dans strava_comment_raw (couche bronze).
    Ne fait rien si la liste est vide.
    """
    if not comments_json:
        return
    sql = "INSERT INTO strava_comment_raw (id_strava, raw_comment) VALUES (%s, %s);"
    with conn.cursor() as cur:
        cur.executemany(sql, [
            (id_strava, json.dumps(comment))
            for comment in comments_json
        ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=== Simulation nouvelle activite Strava ===")

    try:
        conn = get_connection()
        logger.info("Connexion PostgreSQL etablie")
    except Exception as exc:
        logger.error("Impossible de se connecter à PostgreSQL : %s", exc)
        return


    try:
        # Selection d'un salarie sportif au hasard
        result = get_random_sportif(conn)
        if result is None:
            logger.error("Aucun salarie sportif trouve en base.")
            return

        id_athlete, sport = result
        logger.info("Salarie sportif selectionne : id_athlete=%s, sport=%s", id_athlete, sport)

        # Génération des métriques de l'activité
        (distance, moving_time_sec, elapsed_time_sec,
         avg_speed, max_speed, avg_watt, max_watt) = generate_activity_metrics(sport)

        start_dt  = datetime.now()
        end_dt    = start_dt + timedelta(seconds=elapsed_time_sec)
        id_strava = generate_unique_strava_id(conn)


        # --- Étape 1 : simulation JSON DetailedActivity (getActivityById) ---
        activity_json = simulate_activity_json(
            id_strava=id_strava,
            id_athlete=id_athlete,
            sport_label=sport,
            start_dt=start_dt,
            end_dt=end_dt,
            distance=distance,
            moving_time_sec=moving_time_sec,
            elapsed_time_sec=elapsed_time_sec,
            avg_speed=avg_speed,
            max_speed=max_speed,
            avg_watt=avg_watt,
            max_watt=max_watt,
        )
        logger.info("JSON DetailedActivity simulé pour id_strava=%s", id_strava)


        # --- Étape 2 : simulation JSON Comments (getCommentsByActivityId) ---
        comments_json = simulate_comments_json(id_strava)
        logger.info(
            "%d commentaire(s) simulé(s) pour id_strava=%s",
            len(comments_json), id_strava
        )


        # --- Étape 3 : stockage brut dans strava_raw ---
        store_raw_activity(conn, id_strava, activity_json)
        logger.info("Activité stockée dans strava_raw")


        # Étape 4 : stockage brut dans strava_comment_raw si commentaire présent (bronze)
        store_raw_comments(conn, id_strava, comments_json)
        if comments_json:
            logger.info(
                "%d commentaire(s) stocké(s) dans strava_comment_raw (bronze)",
                len(comments_json)
            )

        conn.commit()
        logger.info(
            "=== Couche validée pour id_strava=%s, "
            "lancer etl_strava.py===",
            id_strava
        )


    except Exception as exc:
        logger.error("Erreur lors de la simulation : %s", exc)
        conn.rollback()
    finally:
        conn.close()
        logger.info("Connexion PostgreSQL fermee.")


if __name__ == "__main__":
    main()