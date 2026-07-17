"""
pipeline_live.py
----------------
Orchestrateur du pipeline temps réel, simulation d'une nouvelle activité
sportive et transformation.

Équivalent de run_pipeline.py pour le flux live, exécute dans l'ordre :
  1. simulate_strava_activity.py  : génère et stocke les données brutes
  2. etl_strava.py                : transforme les données brutes
                                    (strava + stravathlete + strava_comment)
                                    et déclenche Debezium → Redpanda → Slack

Usage :
  python pipeline_live.py
  python -m pipeline_live
"""

import os
import sys
import logging
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import BASE_DIR
from utils.logging_utils import setup_logging

setup_logging("pipeline_live.log", BASE_DIR)
logger = logging.getLogger(__name__)

SCRIPTS = [
    "scripts/simulate_strava_activity.py",   # bronze : génération + stockage brut
    "scripts/etl_strava.py",                 # gold   : transformation + CDC → Slack
]


def run_script(script_path):
    """
    Exécute un script Python via subprocess.
    Retourne True si le script s'est terminé avec succès, False sinon.
    """
    logger.info("--- Lancement : %s ---", script_path)
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=False,
    )
    if result.returncode != 0:
        logger.error("Échec : %s (code %d)", script_path, result.returncode)
        return False
    logger.info("Succès : %s", script_path)
    return True


def main():
    logger.info("=== Démarrage pipeline live ===")

    for script in SCRIPTS:
        if not run_script(script):
            logger.critical(
                "Pipeline live interrompu à l'étape : %s", script
            )
            sys.exit(1)

    logger.info("=== Pipeline live terminé avec succès ===")


if __name__ == "__main__":
    main()
