"""
data_quality_check.py
-----------------------
Validation de la qualite des donnees APRES import et geocodage.
Etape bloquante : si la validation echoue, le pipeline s'arrete
(code de sortie != 0).

Verifie :
  - table salarie          (coherence post-insertion + dates)
  - table sportpratique    (integrite referentielle + sports connus)
  - salarie_geocode        (couverture complete + coherence distance/eligibilite + GPS France)
  - table strava           (coherence activites generees — ignoree si vide)
  - table strava_comment   (unicite et non-nullite des commentaires — ignoree si vide)

Note : ce script est appele deux fois dans run_pipeline.py :
  - Avant generate_strava_raw.py / etl_strava.py : valide salarie / sportpratique / geocode
  - Apres  generate_strava_raw.py / etl_strava.py : memes verifications + validation strava

Usage :
  python -m scripts.data_quality_check
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from utils.config import BASE_DIR
from utils.db import get_sqlalchemy_engine
from utils.logging_utils import setup_logging
from utils.data_quality import (
    validate_salarie_table,
    validate_sportpratique_table,
    validate_geocode_coverage,
    validate_geocode_table,
    validate_strava_table,
    validate_strava_comment_table,
    format_validation_errors,
)


setup_logging("data_quality_check.log", BASE_DIR)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Demarrage validation qualite des donnees (apres import) ===")

    engine = get_sqlalchemy_engine()
    logger.info("Connexion PostgreSQL etablie (SQLAlchemy)")

    all_success = True

    try:
        # --- salarie ---
        result = validate_salarie_table(engine)
        if not result.success:
            all_success = False
            for err in format_validation_errors(result):
                logger.error("Validation salarie : %s", err)
        else:
            logger.info("Validation salarie : OK")

        # --- sportpratique ---
        result = validate_sportpratique_table(engine)
        if not result.success:
            all_success = False
            for err in format_validation_errors(result):
                logger.error("Validation sportpratique : %s", err)
        else:
            logger.info("Validation sportpratique : OK")

        # --- geocode : couverture complete (4c) ---
        result = validate_geocode_coverage(engine)
        if not result.success:
            all_success = False
            for err in format_validation_errors(result):
                logger.error("Validation geocode couverture : %s", err)
        else:
            logger.info("Validation geocode couverture : OK")

        # --- geocode : coherence distance / eligibilite / GPS (4b) ---
        result = validate_geocode_table(engine)
        if result is None:
            logger.warning(
                "Validation salarie_geocode : aucune ligne geocodee, validation ignoree"
            )
        elif not result.success:
            all_success = False
            for err in format_validation_errors(result):
                logger.error("Validation salarie_geocode : %s", err)
        else:
            logger.info("Validation salarie_geocode : OK")

        # --- strava (4e) — ignoree si la table est vide ---
        result = validate_strava_table(engine)
        if result is None:
            logger.info(
                "Validation strava : table vide — etape generate_strava pas encore executee, skip"
            )
        elif not result.success:
            all_success = False
            for err in format_validation_errors(result):
                logger.error("Validation strava : %s", err)
        else:
            logger.info("Validation strava : OK")

        # --- strava_comment — ignoree si la table est vide ---
        result = validate_strava_comment_table(engine)
        if result is None:
            logger.info("Validation strava_comment : table vide, skip")
        elif not result.success:
            all_success = False
            for err in format_validation_errors(result):
                logger.error("Validation strava_comment : %s", err)
        else:
            logger.info("Validation strava_comment : OK")

    except Exception as exc:
        logger.critical("Erreur inattendue pendant la validation : %s", exc)
        all_success = False

    finally:
        engine.dispose()
        logger.info("Connexion PostgreSQL fermee.")

    if not all_success:
        logger.critical("=== Validation qualite des donnees ECHOUEE ===")
        sys.exit(1)

    logger.info("=== Validation qualite des donnees : SUCCES ===")


if __name__ == "__main__":
    main()
