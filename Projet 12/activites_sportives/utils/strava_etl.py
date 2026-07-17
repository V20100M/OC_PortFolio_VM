"""
utils/strava_etl.py
-------------------
Utilitaires ETL partagés entre generate_strava_raw.py, simulate_strava_activity.py
et etl_strava.py.

Responsabilités :
  1. Simuler un JSON DetailedActivity (format getActivityById de l'API Strava)
  2. Simuler un JSON Comments (format getCommentsByActivityId de l'API Strava)
  3. Parser ces JSONs et insérer les données en base PostgreSQL

"""

import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Commentaires optionnels simulés (probabilité 30%)
# ---------------------------------------------------------------------------
SAMPLE_COMMENTS = [
    "Reprise du sport :)",
    "Belle sortie aujourd'hui !",
    "Jambes lourdes mais on y est !",
    "Nouveau record personnel !",
    "Superbe parcours, je recommande.",
    "Un peu de pluie mais ça valait le coup.",
    "Fatigue mais satisfait(e) !",
]


# ---------------------------------------------------------------------------
# 1. SIMULATION format getActivityById (DetailedActivity)
# ---------------------------------------------------------------------------
def simulate_activity_json(id_strava, id_athlete, sport_label,
                            start_dt, end_dt,
                            distance, moving_time_sec, elapsed_time_sec,
                            avg_speed, max_speed, avg_watt, max_watt):
    """
    Construit un dict au format DetailedActivity de l'API Strava.

    Champs mappés vers la table strava :
        id              → id_strava
        athlete.id      → utilisé dans stravathlete
        sport_type      → sport_type
        start_date      → start_date
        end_date        → calculé depuis start_date + elapsed_time (non natif Strava)
        distance        → distance (mètres)
        moving_time     → moving_time (secondes)
        elapsed_time    → elapsed_time (secondes)
        average_speed   → avg_speed (m/s)
        max_speed       → max_speed (m/s)
        average_watts   → avg_watt (optionnel)
        max_watts       → max_watt (optionnel)

    EN PRODUCTION, on peut remplacer l'intégralité de cette fonction par :
        response = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()
    """
    return {
        "id": id_strava,
        "resource_state": 3,
        "athlete": {
            "id": id_athlete,
            "resource_state": 1
        },
        "name": sport_label,                        # nom affiché sur Strava
        "sport_type": sport_label,                  # type de sport (Run, Ride, etc.)
        "distance": distance if distance else 0,    # en mètres, 0 si non pertinent
        "moving_time": moving_time_sec,             # temps effectif en mouvement (s)
        "elapsed_time": elapsed_time_sec,           # durée totale (s)
        "start_date": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start_date_local": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        # end_date est une extension locale : Strava ne le fournit pas nativement
        # En prod, on le calcule : start_date + elapsed_time
        "_end_date": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "average_speed": avg_speed if avg_speed else 0,   # m/s
        "max_speed": max_speed if max_speed else 0,       # m/s
        "average_watts": avg_watt,                        # None si non applicable
        "max_watts": max_watt,                            # None si non applicable
        "manual": True,                                   # activité saisie manuellement
        "trainer": False,
        "commute": False,
    }


# ---------------------------------------------------------------------------
# 2. SIMULATION format getCommentsByActivityId (Comment[])
# ---------------------------------------------------------------------------
def simulate_comments_json(id_strava):
    """
    Construit une liste de commentaires au format API Strava.

    Champs mappés :
        text → colonne commentaire dans la table strava
        (les autres champs sont ignorés pour ce POC)

    Probabilité d'avoir un commentaire : 30% (cohérent avec les données réelles Strava).

    EN PRODUCTION — remplacer l'intégralité de cette fonction par :
        response = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}/comments",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()  # retourne une liste, vide si aucun commentaire
    """
    # 30% de chance qu'un commentaire soit présent
    if random.random() > 0.3:
        return []   # liste vide = pas de commentaire, comme l'API Strava

    return [
        {
            "id": random.randint(10000000, 99999999),
            "activity_id": id_strava,
            "post_id": None,
            "resource_state": 2,
            "text": random.choice(SAMPLE_COMMENTS),
            "mentions_metadata": None,
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "athlete": {
                "firstname": "Salarié",
                "lastname": "SDS"
            },
            "cursor": None
        }
    ]


# ---------------------------------------------------------------------------
# 3. ETL parsing des JSONs et préparation du tuple pour PostgreSQL
# ---------------------------------------------------------------------------
def parse_activity_and_comments(activity_json, comments_json):
    """
    Parse un DetailedActivity et sa liste de commentaires Strava,
    et retourne un tuple prêt pour l'insertion en base.

    C'est cette fonction qui constitue la couche ETL :
    elle est identique qu'on vienne de données simulées ou de l'API réelle.

    Retourne :
        activity_data  : tuple (id_strava, id_athlete, start_dt, end_dt, sport_type,
                                distance, moving_time, elapsed_time,
                                avg_speed, max_speed, avg_watt, max_watt)
        comments_data  : liste de tuples (id_comment, id_strava, texte, auteur, created_at)

    Raises:
        ValueError si les champs obligatoires sont absents ou invalides.
    """
    # --- Extraction des champs obligatoires ---
    try:
        id_strava = int(activity_json["id"])
        id_athlete = int(activity_json["athlete"]["id"])
        sport_type = str(activity_json["sport_type"])
        elapsed_time = int(activity_json["elapsed_time"])
        moving_time = int(activity_json["moving_time"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Champ obligatoire manquant ou invalide : {exc}") from exc

    # --- Parsing des dates ---
    start_dt = _parse_date(activity_json.get("start_date") or activity_json.get("start_date_local"))
    # end_date : extension locale (non fourni par Strava, calculé)
    end_dt_raw = activity_json.get("_end_date")
    if end_dt_raw:
        end_dt = _parse_date(end_dt_raw)
    else:
        # Fallback : calcul depuis start_date + elapsed_time
        end_dt = start_dt + timedelta(seconds=elapsed_time)

    # --- Champs optionnels (None si absent) ---
    distance = _safe_float(activity_json.get("distance"))
    avg_speed = _safe_float(activity_json.get("average_speed"))
    max_speed = _safe_float(activity_json.get("max_speed"))
    avg_watt = _safe_float(activity_json.get("average_watts"))
    max_watt = _safe_float(activity_json.get("max_watts"))

    # Convertit 0 en None pour distance/vitesse (sports sans déplacement)
    distance = None if distance == 0 else distance
    avg_speed = None if avg_speed == 0 else avg_speed
    max_speed = None if max_speed == 0 else max_speed


    activity_data = (
        id_strava, id_athlete,
        start_dt, end_dt,
        sport_type,
        distance, moving_time, elapsed_time,
        avg_speed, max_speed, avg_watt, max_watt,
    )

    # --- Parsing des commentaires (0 à N) ---
    # Chaque commentaire de l'API Strava devient une ligne dans strava_comment
    comments_data = [
        (
            int(c["id"]),
            id_strava,
            c.get("text"),
            f"{c['athlete'].get('firstname', '')} {c['athlete'].get('lastname', '')}".strip(),
            _parse_date(c.get("created_at")),
        )
        for c in comments_json
        if c.get("id")  # ignore les entrées malformées
    ]

    logger.debug(
        "Activité parsée : id_strava=%s, athlete=%s, sport=%s, distance=%s, nb_comments=%d",
        id_strava, id_athlete, sport_type, distance, len(comments_data)
    )

    return activity_data, comments_data

# ---------------------------------------------------------------------------
# 4. INSERTION en base (partagée entre les deux scripts)
# ---------------------------------------------------------------------------
def insert_parsed_activity(conn, activity_data, comments_data):
    """
    Insère une activité parsée dans les tables strava, stravathlete et strava_comment.

    Args:
        conn           : connexion psycopg2 active
        activity_data  : tuple retourné par parse_activity_and_comments()
        comments_data  : liste de tuples retournée par parse_activity_and_comments()

    Returns:
        id_strava inséré

    Raises:
        Exception en cas d'erreur DB (le commit/rollback est géré par l'appelant)
    """
    (id_strava, id_athlete,
     start_dt, end_dt,
     sport_type,
     distance, moving_time, elapsed_time,
     avg_speed, max_speed, avg_watt, max_watt) = activity_data

    with conn.cursor() as cur:
        # Insertion dans strava
        cur.execute("""
            INSERT INTO strava (
                id_strava, start_date, end_date, sport_type,
                distance, moving_time, elapsed_time,
                avg_speed, max_speed, avg_watt, max_watt
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_strava) DO NOTHING;
        """, (
            id_strava, start_dt, end_dt, sport_type,
            distance, moving_time, elapsed_time,
            avg_speed, max_speed, avg_watt, max_watt,
        ))

        # Insertion dans stravathlete (correspondance activité / athlete)
        cur.execute("""
            INSERT INTO stravathlete (id_strava, id_athlete)
            VALUES (%s, %s)
            ON CONFLICT (id_strava) DO NOTHING;
        """, (id_strava, id_athlete))

        # Insertion dans strava_comment (0 à N commentaires)
        if comments_data:
            cur.executemany("""
                INSERT INTO strava_comment (id_comment, id_strava, texte, auteur, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id_comment) DO NOTHING;
            """, comments_data)
            logger.debug(
                "%d commentaire(s) insérés pour id_strava=%s",
                len(comments_data), id_strava
            )

    return id_strava


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------
def _parse_date(date_str):
    """Parse une date Strava en datetime Python."""
    if not date_str:
        raise ValueError("Date manquante")
    # Strava utilise le format "2018-02-16T14:52:54Z"
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value):
    """Convertit une valeur en float, retourne None si None ou non convertible."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
