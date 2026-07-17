"""
geocode_adresses.py
-------------------
Geocode les adresses domicile des salaries via Nominatim (OpenStreetMap),
calcule la distance domicile -> bureau via OSRM,
et determine l'eligibilite a la prime sportive.

Tables alimentees :
  - salarie_geocode (latitude, longitude, distance_km, eligible_prime)

Regles d'eligibilite prime :
  - Marche/running          : distance <= 15 km
  - Velo/Trottinette/Autres : distance <= 25 km
  - Voiture/TC              : non eligible (pas de calcul OSRM)

Optimisation :
  Un salarié n'est regéocodé que si son adresse ou son moyen de déplacement
  a changé depuis le dernier géocodage réussi. Les salariés inchangés sont
  ignorés pour respecter la limite Nominatim et réduire le temps d'exécution.

Fallbacks geocodage si adresse introuvable :
  1. Adresse originale + ", France"
  2. Sans le numero de rue
  3. Avec le numero 1 en remplacement

Usage :
  python geocode_adresses.py

Prerequis :
  - import_excel.py doit avoir ete execute avec succes
  - pip install requests
  - Nominatim : max 1 requete/seconde (respect automatique)
"""

import os
import re
import sys
import time
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from utils.db import get_connection
from utils.logging_utils import setup_logging
from utils.config import (
    BASE_DIR,
    BUREAU_ADRESSE,
    NOMINATIM_URL,
    NOMINATIM_DELAY,
    USER_AGENT,
    OSRM_URL,
    OSRM_PROFILES,
    SEUILS,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
setup_logging("geocode_adresses.log", BASE_DIR)
logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Geocodage via Nominatim
# ---------------------------------------------------------------------------
def geocode_adresse(adresse: str) -> tuple | None:
    """
    Retourne (latitude, longitude) pour une adresse donnee.
    Retourne None si le geocodage echoue.
    Respecte la limite de 1 requete/seconde de Nominatim.
    """
    params = {
        "q":            adresse,
        "format":       "json",
        "limit":        1,
        "countrycodes": "fr",
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
        logger.warning("Geocodage sans resultat pour : %s", adresse)
        return None
    except Exception as exc:
        logger.error("Erreur geocodage '%s' : %s", adresse, exc)
        return None
    finally:
        time.sleep(NOMINATIM_DELAY)


def geocode_avec_fallback(adresse: str) -> tuple | None:
    """
    Tente de geocoder une adresse avec trois strategies successives :
      1. Adresse originale
      2. Sans le numero de rue (ex: "Rue des Pins, 34000" au lieu de "12 Rue des Pins, 34000")
      3. Avec le numero 1 en remplacement (pour les rues sans numero dans OSM)
    """
    # Tentative 1 : adresse originale
    coords = geocode_adresse(adresse + ", France")
    if coords:
        return coords

    # Tentative 2 : sans le numero de rue
    adresse_sans_numero = re.sub(r'^\d+\s+(Bis\s+|Ter\s+)?', '', adresse, flags=re.IGNORECASE)
    if adresse_sans_numero != adresse:
        logger.info("  Fallback sans numero : %s", adresse_sans_numero)
        coords = geocode_adresse(adresse_sans_numero + ", France")
        if coords:
            return coords

    # Tentative 3 : avec numero 1
    if re.match(r'^\d+', adresse):
        adresse_numero_1 = re.sub(r'^\d+', '1', adresse)
    else:
        adresse_numero_1 = "1 " + adresse
    logger.info("  Fallback numero 1 : %s", adresse_numero_1)
    coords = geocode_adresse(adresse_numero_1 + ", France")
    return coords


# ---------------------------------------------------------------------------
# Calcul de distance via OSRM
# ---------------------------------------------------------------------------
def calcule_distance_osrm(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    profile: str,
) -> float | None:
    """
    Retourne la distance en km entre deux points via OSRM.
    Retourne None en cas d'erreur.
    """
    url = OSRM_URL.format(
        profile=profile,
        lng1=lng1, lat1=lat1,
        lng2=lng2, lat2=lat2,
    )
    try:
        resp = requests.get(url, params={"overview": "false"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "Ok":
            distance_m = data["routes"][0]["distance"]
            return round(distance_m / 1000, 2)
        logger.warning("OSRM code non-Ok : %s", data.get("code"))
        return None
    except Exception as exc:
        logger.error("Erreur OSRM : %s", exc)
        return None


# ---------------------------------------------------------------------------
# Insertion ou mise à jour en base
# ---------------------------------------------------------------------------
def upsert_geocode(conn, id_salarie, latitude, longitude, geocode_ok,
                   distance_km, eligible_prime):
    """
    Insère ou met à jour les données de géocodage pour un salarié.
    Utilise ON CONFLICT pour gérer les mises à jour (adresse ou moyen changé).
    """
    sql = """
        INSERT INTO salarie_geocode (
            id_salarie, latitude, longitude, geocode_ok,
            distance_km, eligible_prime
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_salarie) DO UPDATE SET
            latitude       = EXCLUDED.latitude,
            longitude      = EXCLUDED.longitude,
            geocode_ok     = EXCLUDED.geocode_ok,
            distance_km    = EXCLUDED.distance_km,
            eligible_prime = EXCLUDED.eligible_prime;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            id_salarie, latitude, longitude, geocode_ok,
            distance_km, eligible_prime,
        ))
    conn.commit()


# ---------------------------------------------------------------------------
# Comparaison avec les données déjà géocodées en base
# ---------------------------------------------------------------------------
def get_deja_geocodes(conn) -> dict:
    """
    Retourne un dict {id_salarie: (adresse_domicile, moyen_deplacement)}
    pour les salariés déjà géocodés avec succès (geocode_ok = TRUE).

    Utilisé pour éviter de regéocoder les salariés dont l'adresse
    et le moyen de déplacement n'ont pas changé.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT s.id_salarie, s.adresse_domicile, s.moyen_deplacement
            FROM salarie s
            JOIN salarie_geocode sg ON s.id_salarie = sg.id_salarie
            WHERE sg.geocode_ok = TRUE;
        """)
        return {
            str(row[0]): (row[1], row[2])
            for row in cur.fetchall()
        }


def filtrer_salaries_a_traiter(salaries, deja_geocodes) -> tuple:
    """
    Compare la liste des salariés en base avec les données déjà géocodées.

    Un salarié est retenu pour géocodage si :
      - Il n'a jamais été géocodé (nouveau salarié)
      - Son adresse domicile a changé
      - Son moyen de déplacement a changé (impacte l'éligibilité et le profil OSRM)

    Retourne :
        (salaries_a_traiter, nb_skipped)
    """
    a_traiter = []
    skipped   = 0

    for id_salarie, adresse, moyen in salaries:
        existant = deja_geocodes.get(str(id_salarie))

        if existant is None:
            # Nouveau salarié donc jamais géocodé
            a_traiter.append((id_salarie, adresse, moyen))

        elif existant[0] != adresse or existant[1] != moyen:
            # Changement détecté
            logger.info(
                "Salarié %s — changement détecté :"
                " adresse '%s' → '%s' / moyen '%s' → '%s'",
                id_salarie, existant[0], adresse, existant[1], moyen
            )
            a_traiter.append((id_salarie, adresse, moyen))

        else:
            # Aucun changement — skip
            skipped += 1

    return a_traiter, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=== Demarrage geocodage adresses ===")

    conn = None
    try:
        conn = get_connection()
        logger.info("Connexion PostgreSQL etablie")

        # Geocodage du bureau une seule fois
        logger.info("Geocodage de l'adresse du bureau...")
        bureau_coords = geocode_adresse(BUREAU_ADRESSE)
        if not bureau_coords:
            logger.critical("Impossible de geocoder l'adresse du bureau.")
            return
        bureau_lat, bureau_lng = bureau_coords
        logger.info("Bureau : lat=%.6f, lng=%.6f", bureau_lat, bureau_lng)

        # Recupere tous les salaries et leurs adresses/moyens
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_salarie, adresse_domicile, moyen_deplacement
                FROM salarie
                ORDER BY id_salarie;
            """)
            salaries = cur.fetchall()
        logger.info("%d salaries en base", len(salaries))

        # Récupère les salariés déjà géocodés avec succès pour éviter de les regéocoder
        deja_geocodes = get_deja_geocodes(conn)
        logger.info("%d salaries deja geocodes avec succes", len(deja_geocodes))

        # Filtre les salariés à traiter, uniquement les nouveaux ou ceux dont l'adresse/moyen a changé
        salaries_a_traiter, skipped = filtrer_salaries_a_traiter(salaries, deja_geocodes)
        logger.info("%d salaries à geocoder, %d skipped", len(salaries_a_traiter), skipped)

        if not salaries_a_traiter:
            logger.info("Aucun salarié à regéocoder.")
            return

        success = errors = non_eligible = 0

        for id_salarie, adresse, moyen in salaries_a_traiter:
            logger.info("Traitement salarie %s — %s", id_salarie, adresse)

            # Geocodage domicile avec fallbacks
            coords = geocode_avec_fallback(adresse)
            if not coords:
                logger.warning("  Echec geocodage apres tous les fallbacks")
                upsert_geocode(conn, id_salarie, None, None, False, None, False)
                errors += 1
                continue

            dom_lat, dom_lng = coords

            # Calcul distance si moyen sportif
            profile     = OSRM_PROFILES.get(moyen)
            distance_km = None
            eligible    = False

            if profile:
                distance_km = calcule_distance_osrm(
                    dom_lat, dom_lng,
                    bureau_lat, bureau_lng,
                    profile,
                )
                if distance_km is not None:
                    seuil    = SEUILS[moyen]
                    eligible = distance_km <= seuil
                    logger.info(
                        "  Distance : %.2f km (seuil %g km) -> %s",
                        distance_km, seuil,
                        "ELIGIBLE" if eligible else "NON ELIGIBLE",
                    )
            else:
                logger.info("  Moyen non sportif (%s) -> non eligible", moyen)
                non_eligible += 1

            upsert_geocode(
                conn, id_salarie,
                dom_lat, dom_lng, True,
                distance_km, eligible,
            )
            success += 1

        logger.info(
            "=== Geocodage termine : %d succes, %d erreurs, %d non sportifs ===",
            success, errors, non_eligible,
        )

    except Exception as exc:
        logger.error("Erreur inattendue : %s", exc)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logger.info("Connexion PostgreSQL fermee.")


if __name__ == "__main__":
    main()