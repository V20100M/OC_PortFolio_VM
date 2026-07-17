"""
import_excel.py
---------------
Importe les donnees des fichiers Excel RH et Sportif dans PostgreSQL.

Tables alimentees :
  - Salarie       (depuis Donnees+RH.xlsx)
  - Sportpratique (depuis Donnees+Sportive.xlsx, salaries avec sport declare)

Usage :
  python import_excel.py

Prerequis :
  - Fichier .env avec les credentials PostgreSQL
  - pip install pandas psycopg2-binary python-dotenv openpyxl
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import re
from datetime import datetime, date
from utils.config import get_rh_file, get_sport_file, ADDRESS_REPLACEMENTS, BASE_DIR
from utils.helpers import is_sport_valide

from utils.logging_utils import setup_logging

from utils.data_quality import (
    validate_salarie_df,
    validate_sportpratique_df,
    format_validation_errors,
)

import pandas as pd
from utils.db import get_connection


# ---------------------------------------------------------------------------
# Logging : StreamHandler via sys.stdout.buffer (robuste IDEs, pytest, redirection)
#           + FileHandler UTF-8 dans logs/
# ---------------------------------------------------------------------------
setup_logging("import_excel.log", BASE_DIR)
logger = logging.getLogger(__name__)


def normalize_address(addr):
    if not isinstance(addr, str):
        return addr
    addr = addr.strip()
    for pattern, replacement in ADDRESS_REPLACEMENTS:
        addr = re.sub(pattern, replacement, addr, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", addr)


# ---------------------------------------------------------------------------
# Conversion des dates Excel
# Note : avec dtype=str, les dates arrivent toujours comme chaines ou serials.
# Le bloc isinstance(datetime/date) est conserve par securite si dtype=str
# est retire a l'avenir.
# ---------------------------------------------------------------------------
def excel_date_to_python(value):
    """Convertit un numero de serie Excel ou une date existante en date Python."""
    if pd.isna(value):
        return None
    # Si c'est déjà un objet date/datetime
    if isinstance(value, (datetime, date)):
        return value if isinstance(value, date) else value.date()
    # Si c'est une chaine texte au format date lisible
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        # Aucun format ne correspond : on laisse tomber sur la conversion seriale ci-dessous
    # Si c'est un numero serial Excel (ou une chaine numerique type "45234")
    try:
        serial = int(float(value))
        # Excel considere a tort 1900 comme une annee bissextile
        if serial > 59:
            serial -= 1
        return (pd.Timestamp("1899-12-31") + pd.Timedelta(days=serial)).date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Chargement des fichiers Excel
# ---------------------------------------------------------------------------
def load_rh_data():
    rh_file = get_rh_file()
    logger.info("Lecture de %s", rh_file)
    df = pd.read_excel(rh_file, dtype=str)

    df.columns = df.columns.str.strip()

    col_map = {
        df.columns[0]:  "id_salarie",
        df.columns[1]:  "nom",
        df.columns[2]:  "prenom",
        df.columns[3]:  "date_naissance",
        df.columns[4]:  "bu",
        df.columns[5]:  "date_embauche",
        df.columns[6]:  "salaire_brut",
        df.columns[7]:  "type_contrat",
        df.columns[8]:  "jours_cp",
        df.columns[9]:  "adresse_domicile",
        df.columns[10]: "moyen_deplacement",
    }
    df = df.rename(columns=col_map)

    for col in ["id_salarie", "nom", "prenom", "bu", "type_contrat", "moyen_deplacement"]:
        df[col] = df[col].astype(str).str.strip()

    df["date_naissance"]   = df["date_naissance"].apply(excel_date_to_python)
    df["date_embauche"]    = df["date_embauche"].apply(excel_date_to_python)
    df["salaire_brut"]     = pd.to_numeric(df["salaire_brut"], errors="coerce")
    df["jours_cp"]         = pd.to_numeric(df["jours_cp"], errors="coerce")
    df["adresse_domicile"] = df["adresse_domicile"].apply(normalize_address)

    logger.info("%d salaries charges depuis le fichier RH", len(df))
    return df


def load_sport_data():
    sport_file = get_sport_file()
    logger.info("Lecture de %s", sport_file)
    df = pd.read_excel(sport_file, dtype=str)
    df.columns = df.columns.str.strip()

    col_map = {
        df.columns[0]: "id_salarie",
        df.columns[1]: "pratique_sport",
    }
    df = df.rename(columns=col_map)

    df["id_salarie"]     = df["id_salarie"].astype(str).str.strip()
    df["pratique_sport"] = df["pratique_sport"].str.strip()

    df = df[is_sport_valide(df["pratique_sport"])]
    logger.info("%d salaries avec un sport declare", len(df))
    return df


# ---------------------------------------------------------------------------
# Insertions en base
# ---------------------------------------------------------------------------
def insert_salaries(conn, df_rh):
    sql = """
        INSERT INTO salarie (
            id_salarie, nom, prenom, date_naissance, bu,
            date_embauche, salaire_brut, type_contrat,
            jours_cp, adresse_domicile, moyen_deplacement
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_salarie) DO UPDATE SET
            nom               = EXCLUDED.nom,
            prenom            = EXCLUDED.prenom,
            date_naissance    = EXCLUDED.date_naissance,
            bu                = EXCLUDED.bu,
            date_embauche     = EXCLUDED.date_embauche,
            salaire_brut      = EXCLUDED.salaire_brut,
            type_contrat      = EXCLUDED.type_contrat,
            jours_cp          = EXCLUDED.jours_cp,
            adresse_domicile  = EXCLUDED.adresse_domicile,
            moyen_deplacement = EXCLUDED.moyen_deplacement;
    """
    success = errors = 0
    for _, row in df_rh.iterrows():
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    row["id_salarie"],
                    row["nom"],
                    row["prenom"],
                    row["date_naissance"],
                    row["bu"],
                    row["date_embauche"],
                    row["salaire_brut"] if pd.notna(row["salaire_brut"]) else None,
                    row["type_contrat"],
                    int(row["jours_cp"]) if pd.notna(row["jours_cp"]) else None,
                    row["adresse_domicile"],
                    row["moyen_deplacement"],
                ))
            conn.commit()
            success += 1
        except Exception as exc:
            logger.error("Erreur insertion salarie %s : %s", row["id_salarie"], exc)
            conn.rollback()
            errors += 1
    logger.info("Salarie : %d inseres/mis a jour, %d erreurs", success, errors)


def insert_sport_pratique(conn, df_sport):
    sql = """
        INSERT INTO sportpratique (id_salarie, pratique_sport)
        VALUES (%s, %s)
        ON CONFLICT (id_salarie) DO UPDATE SET
            pratique_sport = EXCLUDED.pratique_sport;
    """
    success = errors = 0
    for _, row in df_sport.iterrows():
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (row["id_salarie"], row["pratique_sport"]))
            conn.commit()
            success += 1
        except Exception as exc:
            logger.error(
                "Erreur insertion sportpratique %s : %s", row["id_salarie"], exc
            )
            conn.rollback()
            errors += 1
    logger.info("Sportpratique : %d inseres/mis a jour, %d erreurs", success, errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=== Demarrage de l'import Excel ===")

    conn = None
    try:
        df_rh    = load_rh_data()
        df_sport = load_sport_data()

        result_salarie = validate_salarie_df(df_rh)
        if not result_salarie.success:
            for err in format_validation_errors(result_salarie):
                logger.error("DQ salarie : %s", err)
            logger.critical("Validation salarie echouee — import annule.")
            return

        salarie_ids = set(df_rh["id_salarie"])
        result_sport = validate_sportpratique_df(df_sport, salarie_ids)
        if not result_sport.success:
            for err in format_validation_errors(result_sport):
                logger.error("DQ sportpratique : %s", err)
            logger.critical("Validation sportpratique echouee — import annule.")
            return

        logger.info("Validation qualite des donnees : OK")

        conn = get_connection()
        logger.info("Connexion PostgreSQL etablie")

        insert_salaries(conn, df_rh)
        insert_sport_pratique(conn, df_sport)
        logger.info("=== Import termine avec succes ===")

    except EnvironmentError as exc:
        logger.critical("%s", exc)
    except FileNotFoundError as exc:
        logger.critical("Fichier source introuvable : %s", exc)
    except Exception as exc:
        logger.error("Erreur inattendue : %s", exc)
        if conn is not None:
            conn.rollback()
    finally:
        if conn is not None:
            conn.close()
            logger.info("Connexion PostgreSQL fermee.")


if __name__ == "__main__":
    main()