"""
database.py
-----------
Connexion PostgreSQL partagée pour le backend Puls-Events.
"""

import os
import logging
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from utils.logging_utils import get_domain_logger

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = get_domain_logger("database", "database.log", BASE_DIR)


def get_connection():
    """Ouvre une nouvelle connexion PostgreSQL à partir des variables d'environnement."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
        )
        return conn
    except psycopg2.OperationalError as e:
        logger.error("Impossible de se connecter à PostgreSQL : %s", e)
        raise


def get_dict_cursor(conn):
    """Retourne un curseur qui renvoie les lignes sous forme de dict."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)