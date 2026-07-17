"""
strava_generation.py
---------------------
Logique partagee de generation des metriques d'une activite sportive
(distance, durees, vitesses, watts) selon les regles par sport.

Utilise par :
  - scripts/generate_strava_raw.py      (generation en masse, bronze)
  - scripts/simulate_strava_activity.py (simulation temps reel)
"""

import random
import unicodedata

from .config import SPORT_RULES


def normalize_sport(label):
    """Normalise le label sport pour matcher les cles de SPORT_RULES."""
    label = label.strip().lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', label)
        if unicodedata.category(c) != 'Mn'
    )


def resolve_sport_rules(sport_label):
    """
    Retourne le dict de regles correspondant au sport.
    Ordre de priorite : lookup exact → correspondance partielle → regles par defaut.
    """
    key = normalize_sport(sport_label)
    if key in SPORT_RULES:
        return SPORT_RULES[key]
    for rule_key in SPORT_RULES:
        if rule_key in key or key in rule_key:
            return SPORT_RULES[rule_key]
    return {
        "distance": None,
        "moving_time": (30, 120),
        "avg_speed_kmh": None,
        "avg_watt": None,
        "max_watt": None,
    }


def generate_activity_metrics(sport_label):
    """
    Genere les metriques d'une activite (distance, durees, vitesses, watts)
    selon les regles du sport.
    Retourne : (distance, moving_time_sec, elapsed_time_sec,
                avg_speed, max_speed, avg_watt, max_watt)
    """
    rules = resolve_sport_rules(sport_label)

    moving_time_min  = random.randint(*rules["moving_time"])
    moving_time_sec  = moving_time_min * 60
    elapsed_time_sec = moving_time_sec + random.randint(0, 15) * 60

    distance  = None
    avg_speed = None
    max_speed = None

    if rules["avg_speed_kmh"]:
        avg_speed_kmh = round(random.uniform(*rules["avg_speed_kmh"]), 2)
        distance      = int(avg_speed_kmh * 1000 / 3600 * moving_time_sec)
        max_speed_kmh = round(avg_speed_kmh * random.uniform(1.1, 1.5), 2)

        # Conversion en m/s pour stockage coherent avec consumer_slack.py
        avg_speed = round(avg_speed_kmh / 3.6, 2)
        max_speed = round(max_speed_kmh / 3.6, 2)
    elif rules["distance"]:
        distance = random.randint(*rules["distance"])


    avg_watt = None
    max_watt = None

    if rules["avg_watt"]:
        avg_watt = random.randint(*rules["avg_watt"])
        max_watt = random.randint(*rules["max_watt"])

    return distance, moving_time_sec, elapsed_time_sec, avg_speed, max_speed, avg_watt, max_watt