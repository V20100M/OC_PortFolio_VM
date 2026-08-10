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

    A utiliser pour les scripts autonomes (un seul point d'entree par
    processus). Pour une application multi-modules (ex: backend FastAPI
    avec plusieurs routers), preferer get_domain_logger() ci-dessous.

    Note:
        Apres l'appel, chaque script recupere son propre logger via :
        logger = logging.getLogger(__name__)
    """
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    try:
        stdout_stream = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    except (ValueError, AttributeError):
        # sys.stdout.buffer indisponible ou deja ferme (ex: sous-processus
        # uvicorn --reload sur Windows) : on retombe sur stdout tel quel.
        stdout_stream = sys.stdout

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(stream=stdout_stream),
            logging.FileHandler(
                os.path.join(log_dir, log_filename), encoding="utf-8"
            ),
        ],
    )


def get_domain_logger(name: str, log_filename: str, base_dir: str) -> logging.Logger:
    """
    Cree (ou recupere) un logger nomme 'name', avec ses propres handlers
    (console + fichier dedie), independant du logger racine.

    A utiliser dans une application multi-modules (ex: backend FastAPI) ou
    plusieurs domaines doivent chacun ecrire dans leur propre fichier de
    log, sans se marcher dessus via logging.basicConfig().

    Exemple :
        logger = get_domain_logger("auth", "auth.log", BASE_DIR)
    """
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)

    if logger.handlers:
        # Deja configure (ex: rechargement du module par uvicorn --reload)
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False  # n'envoie pas les messages vers le logger racine

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    try:
        stdout_stream = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    except (ValueError, AttributeError):
        stdout_stream = sys.stdout

    console_handler = logging.StreamHandler(stream=stdout_stream)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        os.path.join(log_dir, log_filename), encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger