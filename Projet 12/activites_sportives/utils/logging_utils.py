"""
logging_utils.py
----------------
Configuration du logging partagee entre les scripts du projet.
"""

import io
import os
import sys
import logging


def setup_logging(log_filename: str, base_dir: str) -> None:
    """
    Configure le systeme de logging avec :
      - StreamHandler UTF-8 robuste (IDEs, pytest, redirection)
      - FileHandler UTF-8 dans le sous-dossier logs/

    Args:
        log_filename : nom du fichier log (ex: "import_excel.log")
        base_dir     : repertoire racine du projet (BASE_DIR depuis config.py)

    Note:
        Apres l'appel, chaque script recupere son propre logger via :
        logger = logging.getLogger(__name__)
    """
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(
                stream=io.TextIOWrapper(
                    sys.stdout.buffer, encoding="utf-8", errors="replace"
                )
            ),
            logging.FileHandler(
                os.path.join(log_dir, log_filename), encoding="utf-8"
            ),
        ],
    )