"""
update_salaries.py
------------------
Orchestrateur de mise à jour des données salariés.
A utiliser après modification du fichier Données+RH.xlsx.

Exécute dans l'ordre :
  1. scripts/import_excel.py       : upsert des données RH
  2. scripts/geocode_adresses.py   : regéocodage des adresses modifiées uniquement
  3. scripts/data_quality_check.py : validation qualité post-mise à jour

Usage :
  docker compose run --rm pipeline python update_salaries.py
"""

import os
import sys
import logging
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import BASE_DIR
from utils.logging_utils import setup_logging

setup_logging("update_salaries.log", BASE_DIR)
logger = logging.getLogger(__name__)

SCRIPTS = [
    "scripts/import_excel.py",
    "scripts/geocode_adresses.py",
    "scripts/data_quality_check.py",
]


def run_script(script_path):
    """
    Exécute un script Python via subprocess.
    Retourne True si succès, False sinon.
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
    logger.info("=== Démarrage mise à jour salariés ===")

    for script in SCRIPTS:
        if not run_script(script):
            logger.critical("Mise à jour interrompue à : %s", script)
            sys.exit(1)

    logger.info("=== Mise à jour terminée avec succès ===")


if __name__ == "__main__":
    main()