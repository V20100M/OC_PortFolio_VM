"""
generate_strava_raw.py
----------------------
Génération et stockage des données brutes Strava.

Pour chaque salarié sportif, génère des activités simulées au format
JSON API Strava (getActivityById + getCommentsByActivityId) et les
stocke telles quelles dans la table strava_raw, sans transformation.

Les données brutes pourront être exploitées de différentes façons
(tables actuelles, analyses ad hoc, replay, etc.) sans avoir à
relancer la génération.

Flux :
  generate_activity_metrics()  :  métriques sportives
  simulate_activity_json()     :  JSON format DetailedActivity
  simulate_comments_json()     :  JSON format Comment[]
  - INSERT INTO strava_raw (raw_activity JSONB, raw_comments JSONB)
  - INSERT INTO strava_comment_raw (un enregistrement par commentaire)

Tables alimentées :
  1. athlete        (id_athlete uniques)
  2. salarieathlete (correspondance id_salarie / id_athlete)
  3. strava_raw     (JSONs bruts non transformés)
  4. strava_comment_raw  (JSONs commentaires bruts)

Usage :
  python -m scripts.generate_strava_raw

Prérequis :
  - import_excel.py doit avoir été exécuté avec succès
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import logging
from datetime import datetime, timedelta

from utils.config import (
    MIN_ACTIVITIES, MAX_ACTIVITIES,
    ATHLETE_ID_MIN, ATHLETE_ID_MAX,
    STRAVA_ID_MIN, STRAVA_ID_MAX,
    BASE_DIR,
)
from utils.strava_generation import generate_activity_metrics
from utils.strava_etl import simulate_activity_json, simulate_comments_json
from utils.logging_utils import setup_logging
from utils.db import get_connection



setup_logging("generate_strava_raw.log", BASE_DIR)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def generate_unique_ids(count, id_min, id_max):
    """Génère count identifiants entiers uniques dans [id_min, id_max]."""
    ids = set()
    while len(ids) < count:
        ids.add(random.randint(id_min, id_max))
    return list(ids)


def random_weekday_datetime(start_dt, end_dt):
    """Retourne un datetime aléatoire en semaine entre 06h et 20h."""
    total_days = (end_dt - start_dt).days
    for _ in range(1000):
        delta = random.randint(0, total_days)
        candidate = start_dt + timedelta(days=delta)
        if candidate.weekday() < 5:
            hour   = random.randint(6, 19)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            return candidate.replace(hour=hour, minute=minute, second=second)
    raise RuntimeError("Impossible de trouver un jour ouvré dans la plage donnée")


def generate_unique_strava_id(used_ids):
    """Génère un id_strava non encore utilisé dans cette session."""
    while True:
        id_strava = random.randint(STRAVA_ID_MIN, STRAVA_ID_MAX)
        if id_strava not in used_ids:
            used_ids.add(id_strava)
            return id_strava


# ---------------------------------------------------------------------------
# Insertions tables de référence
# ---------------------------------------------------------------------------
def insert_athletes(conn, athlete_ids):
    """Étape 1 : insère les id_athlete dans la table athlete."""
    sql = "INSERT INTO athlete (id_athlete) VALUES (%s) ON CONFLICT (id_athlete) DO NOTHING;"
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, [(aid,) for aid in athlete_ids])
        conn.commit()
        logger.info("Athlete : %d insérés", len(athlete_ids))
    except Exception as exc:
        logger.error("Erreur insertion athletes : %s", exc)
        conn.rollback()
        raise


def insert_salarie_athlete(conn, mapping):
    """Étape 2 : insère les correspondances id_salarie / id_athlete."""
    sql = """
        INSERT INTO salarieathlete (id_salarie, id_athlete)
        VALUES (%s, %s)
        ON CONFLICT (id_salarie) DO NOTHING;
    """
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, mapping)
        conn.commit()
        logger.info("Salarieathlete : %d correspondances insérées", len(mapping))
    except Exception as exc:
        logger.error("Erreur insertion salarieathlete : %s", exc)
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Génération et stockage
# ---------------------------------------------------------------------------
def store_raw_activity(conn, id_strava, activity_json):
    """
    Insère un JSON d'activité brut dans strava_raw.
    Un enregistrement par activité, pas de transformation.
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO strava_raw (id_strava, raw_activity) VALUES (%s, %s);",
            (id_strava, json.dumps(activity_json)),
        )


def store_raw_comments(conn, id_strava, comments_json):
    """
    Insère chaque commentaire brut individuellement dans strava_comment_raw.
    Un enregistrement par commentaire permet une exploitation indépendante
    des commentaires sans passer par la table d'activités.
    """
    if not comments_json:
        return  # pas de commentaire pour cette activité

    sql = "INSERT INTO strava_comment_raw (id_strava, raw_comment) VALUES (%s, %s);"
    with conn.cursor() as cur:
        cur.executemany(sql, [
            (id_strava, json.dumps(comment))
            for comment in comments_json
        ])


def generate_and_store_raw(conn, salaries, athlete_ids, period_start, period_end):
    """
    Pour chaque salarié sportif :
      1. Génère N activités entre MIN_ACTIVITIES et MAX_ACTIVITIES
      2. Simule les JSONs Strava (DetailedActivity + Comment[])
      3. Stocke les JSONs bruts dans strava_raw (sans transformation)
      4. Stocke chaque commentaire brut dans strava_comment_raw

    Les données restent dans leur format d'origine API Strava pour
    permettre tout type d'exploitation ultérieure.

    Returns:
        (total_success, total_errors)
    """

    used_strava_ids = set()
    total_success = total_errors = 0

    for (id_salarie, sport), id_athlete in zip(salaries, athlete_ids):
        nb_activities = random.randint(MIN_ACTIVITIES, MAX_ACTIVITIES)
        success_count = 0

        for _ in range(nb_activities):
            try:
                # Génération des métriques sportives
                (distance, moving_time_sec, elapsed_time_sec,
                 avg_speed, max_speed, avg_watt, max_watt) = generate_activity_metrics(sport)

                start_dt  = random_weekday_datetime(period_start, period_end)
                end_dt    = start_dt + timedelta(seconds=elapsed_time_sec)
                id_strava = generate_unique_strava_id(used_strava_ids)

                # Simulation JSON DetailedActivity (getActivityById)
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

                # Simulation JSON Comments (getCommentsByActivityId)
                comments_json = simulate_comments_json(id_strava)

                # Stockage brut, activité et commentaires séparés
                store_raw_activity(conn, id_strava, activity_json)
                store_raw_comments(conn, id_strava, comments_json)
                conn.commit()
                success_count += 1

            except Exception as exc:
                logger.error(
                    "Erreur génération brute salarié %s (athlete %s) : %s",
                    id_salarie, id_athlete, exc
                )
                conn.rollback()
                total_errors += 1

        logger.info(
            "Salarié %s (athlete %s, sport: %s) → %d/%d activités stockées",
            id_salarie, id_athlete, sport, success_count, nb_activities
        )
        total_success += success_count

    return total_success, total_errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=== Démarrage génération données brutes Strava ===")

    try:
        conn = get_connection()
        logger.info("Connexion PostgreSQL établie")
    except Exception as exc:
        logger.critical("Impossible de se connecter à PostgreSQL : %s", exc)
        return

    try:
        # Récupération des salariés sportifs depuis la base
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id_salarie, pratique_sport FROM sportpratique ORDER BY id_salarie;"
            )
            salaries = [(str(r[0]), r[1]) for r in cur.fetchall()]
        logger.info("%d salariés sportifs récupérés", len(salaries))

        if not salaries:
            logger.warning("Aucun salarié sportif trouvé.")
            return

        # Génération des id_athlete uniques
        athlete_ids = generate_unique_ids(len(salaries), ATHLETE_ID_MIN, ATHLETE_ID_MAX)

        # Étape 1 : insertion dans athlete
        insert_athletes(conn, athlete_ids)

        # Étape 2 : insertion dans salarieathlete
        mapping = [
            (id_salarie, id_athlete)
            for (id_salarie, _), id_athlete in zip(salaries, athlete_ids)
        ]
        insert_salarie_athlete(conn, mapping)

        # Période de génération : 12 derniers mois
        period_end   = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = period_end - timedelta(days=365)
        logger.info("Période : %s → %s", period_start.date(), period_end.date())

        # Étape 3 : génération et stockage
        total_success, total_errors = generate_and_store_raw(
            conn, salaries, athlete_ids, period_start, period_end
        )

        logger.info(
            "=== Génération terminée : %d activités stockées dans strava_raw, %d erreurs ===",
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
