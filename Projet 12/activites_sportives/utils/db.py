"""
db.py
-----
Connexion PostgreSQL partagee entre les scripts du pipeline
(import_excel.py, geocode_adresses.py, generate_strava_raw.py, etl_strava.py,
simulate_strava_activity.py, consumer_slack.py).
Charge les credentials depuis .env via python-dotenv.
"""

import os

import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def _get_credentials():
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT")
    dbname   = os.getenv("DB_NAME")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    missing = [k for k, v in {
        "DB_HOST": host, "DB_PORT": port, "DB_NAME": dbname,
        "DB_USER": user, "DB_PASSWORD": password
    }.items() if not v]

    if missing:
        raise EnvironmentError(
            f"Variables manquantes dans .env : {', '.join(missing)}"
        )

    return host, port, dbname, user, password


def get_connection():
    host, port, dbname, user, password = _get_credentials()
    return psycopg2.connect(
        host=host, port=int(port), dbname=dbname,
        user=user, password=password
    )


def get_sqlalchemy_engine():
    """
    Retourne un moteur SQLAlchemy, utilise par pandas.read_sql
    (utils/data_quality.py) pour eviter le UserWarning de pandas
    sur les connexions psycopg2 brutes.
    """
    host, port, dbname, user, password = _get_credentials()
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)