"""
run_pipeline.py
---------------
Lance les scripts du pipeline dans l'ordre sequentiel :
  1. analyse_rh.py           — analyse et visualisation des donnees source
  2. import_excel.py         — import des donnees RH et sportives en base
  3. geocode_adresses.py     — geocodage et calcul d'eligibilite
  4. data_quality_check.py   — validation qualite post-import (bloquant)
  5. generate_strava_raw.py  — generation brute des donnees Strava (bronze)
  6. etl_strava.py           — transformation des donnees Strava (gold)
  7. data_quality_check.py   — validation qualite post-generation (bloquant)

Arret immediat si un script echoue (code de retour non nul).

Usage :
  python run_pipeline.py
"""

import subprocess
import sys
import os
import time
from utils.config import BASE_DIR

SCRIPTS = [
    "scripts/analyse_rh.py",
    "scripts/import_excel.py",
    "scripts/geocode_adresses.py",
    "scripts/data_quality_check.py",   # passe 1 : salarie + sportpratique + geocode (strava skip)
    "scripts/generate_strava_raw.py",
    "scripts/etl_strava.py",
    "scripts/data_quality_check.py",   # passe 2 : idem + validation strava apres generation
]


def run_script(script_name: str) -> bool:
    """
    Lance un script Python et affiche sa sortie en temps reel.
    Retourne True si le script s'est termine avec succes, False sinon.
    """
    script_path = os.path.join(BASE_DIR, script_name)
    print(f"\n{'='*60}")
    print(f"  Lancement : {script_name}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=BASE_DIR,
    )

    if result.returncode != 0:
        print(f"\n[ECHEC] {script_name} a echoue (code {result.returncode})")
        return False

    print(f"\n[OK] {script_name} termine avec succes")
    return True


def main():
    print("=== Demarrage du pipeline ===")

    time.sleep(30)  # petit delai pour s'assurer que la base est prete
    for script in SCRIPTS:
        success = run_script(script)
        if not success:
            print(f"\n[ARRET] Pipeline interrompu apres l'echec de {script}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print("  Pipeline termine avec succes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()