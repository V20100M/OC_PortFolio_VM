"""
config.py
---------
Constantes partagees entre import_excel.py et generate_strava_raw.py.
Charge le .env pour DATA_DIR, SLACK_WEBHOOK_URL et KAFKA_BOOTSTRAP_SERVERS.
Les credentials PostgreSQL restent sous la responsabilite de db.py.

Contextes :
  - Fichiers et adresses  : utilises par import_excel.py
  - SPORT_RULES et IDs    : utilises par generate_strava_raw.py
  - Slack et Kafka        : utilises par consumer_slack.py
"""

import os
from dotenv import load_dotenv
from .helpers import find_file

load_dotenv()

# ---------------------------------------------------------------------------
# Repertoire des fichiers source
# sous-dossier data/ a cote du projet
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")

# ---------------------------------------------------------------------------
# Chemins des fichiers Excel
# (contexte : import_excel.py)
# ---------------------------------------------------------------------------
def get_rh_file():
    return find_file(DATA_DIR, "*RH*.xlsx")


def get_sport_file():
    return find_file(DATA_DIR, "*Sportive*.xlsx")


# ---------------------------------------------------------------------------
# Normalisation des adresses
# (contexte : import_excel.py)
# ---------------------------------------------------------------------------
ADDRESS_REPLACEMENTS = [
    (r"\bBd\b\.?",   "Boulevard"),
    (r"\bAv\b\.?",   "Avenue"),
    (r"\bChem\b\.?", "Chemin"),
    (r"\bRte\b\.?",  "Route"),
    (r"\bSt\b\.?",   "Saint"),
    (r"\bPl\b\.?",   "Place"),
    (r"\bAll\b\.?",  "Allée"),
    (r"\bImp\b\.?",  "Impasse"),
    (r"\bTrav\b\.?", "Traverse"),
    (r"\bHam\b\.?",  "Hameau"),
    (r"\bLot\b\.?",  "Lotissement"),
]


# ---------------------------------------------------------------------------
# Constantes generation Strava
# (contexte : generate_strava_raw.py)
# ---------------------------------------------------------------------------
MIN_ACTIVITIES  = 15  #
MAX_ACTIVITIES  = 80
ATHLETE_ID_MIN  = 100_000
ATHLETE_ID_MAX  = 999_999
STRAVA_ID_MIN   = 1_000_000_000
STRAVA_ID_MAX   = 9_999_999_999

# ---------------------------------------------------------------------------
# Regles par sport — alias pour eviter la duplication (principe DRY)
# (contexte : generate_strava_raw.py)
# ---------------------------------------------------------------------------
_RUNNING_RULES = {
    "distance":     None,
    "moving_time":  (15, 150),
    "avg_speed_kmh": (6, 12),
    "avg_watt":     None,
    "max_watt":     None,
}

SPORT_RULES = {
    "course a pied": _RUNNING_RULES,
    "running": _RUNNING_RULES,
    "runing": _RUNNING_RULES,  # correction faute de frappe dans les donnees source
    "randonnee": {
        "distance": None,
        "moving_time": (45, 240),
        "avg_speed_kmh": (3, 6),
        "avg_watt": None,
        "max_watt": None,
    },
    "velo": {
        "distance": None,
        "moving_time": (30, 150),
        "avg_speed_kmh": (15, 30),
        "avg_watt": (80, 180),
        "max_watt": (150, 300),
    },
    "natation": {
        "distance": None,
        "moving_time": (20, 90),
        "avg_speed_kmh": (1.5, 2.5),
        "avg_watt": None,
        "max_watt": None,
    },
    "football": {
        "distance": None,
        "moving_time": (60, 90),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "rugby": {
        "distance": None,
        "moving_time": (60, 90),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "basketball": {
        "distance": None,
        "moving_time": (60, 120),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "tennis": {
        "distance": None,
        "moving_time": (45, 120),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "badminton": {
        "distance": None,
        "moving_time": (30, 90),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "tennis de table": {
        "distance": None,
        "moving_time": (45, 120),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "escalade": {
        "distance": None,
        "moving_time": (60, 180),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "judo": {
        "distance": None,
        "moving_time": (60, 120),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "boxe": {
        "distance": None,
        "moving_time": (60, 120),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "voile": {
        "distance": (5000, 40000),
        "moving_time": (120, 300),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
    "triathlon": {
        "distance": None,
        "moving_time": (60, 240),
        "avg_speed_kmh": (20.0, 35.0),
        "avg_watt": None,
        "max_watt": None,
    },
    "equitation": {
        "distance": None,
        "moving_time": (30, 90),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    },
}

# Sports feminins ou commencant par une voyelle -> article different de "du"
SPORT_ARTICLES = {
    "natation":   "de la",
    "randonnee":  "de la",
    "marche":     "de la",
    "voile":      "de la",
    "boxe":       "de la",
    "equitation": "de l'",
    "escalade":   "de l'",
}


# ---------------------------------------------------------------------------
# Constantes geocodage et calcul distances
# (contexte : geocode_adresses.py)
# ---------------------------------------------------------------------------
BUREAU_ADRESSE  = "1362 Avenue des Platanes, 34970 Lattes, France"
NOMINATIM_URL   = "https://nominatim.openstreetmap.org/search"
OSRM_URL        = "http://router.project-osrm.org/route/v1/{profile}/{lng1},{lat1};{lng2},{lat2}"
USER_AGENT      = "SportDataSolution/1.0 (poc-avantages-sportifs)"
NOMINATIM_DELAY = 1.1  # secondes entre chaque requete Nominatim

# Seuils d'eligibilite en km
SEUILS = {
    "Marche/running":           15.0,
    "Vélo/Trottinette/Autres":  25.0,
}

# Profils OSRM par moyen de deplacement
OSRM_PROFILES = {
    "Marche/running":           "foot",
    "Vélo/Trottinette/Autres":  "bike",
}