"""
helpers.py
----------
Fonctions utilitaires partagees entre les scripts du projet.
"""

import glob
import os
import warnings


def find_file(directory: str, pattern: str) -> str:
    """
    Retourne le chemin du premier fichier correspondant au pattern dans directory.
    Tri deterministe via sorted(). Warning si plusieurs fichiers correspondent.
    """
    matches = sorted(glob.glob(os.path.join(directory, pattern)))
    if not matches:
        raise FileNotFoundError(f"Aucun fichier '{pattern}' trouve dans {directory}")
    if len(matches) > 1:
        warnings.warn(
            f"Plusieurs fichiers correspondent a '{pattern}' : {matches}. Premier utilise : {matches[0]}",
            UserWarning,
            stacklevel=2,
        )
    return matches[0]


def is_sport_valide(series):
    """
    Retourne un masque booleen : True si le sport est declare et valide.
    Exclut NaN, chaine vide, espaces seuls et chaine 'nan' (pandas/Excel mal formes).

    Usage :
        df = df[is_sport_valide(df["pratique_sport"])]           # filtrage
        df["pratique_sport"] = is_sport_valide(df["pratique_sport"])  # flag booleen
    """
    return (
        series.notna() &
        (series.str.strip() != "") &
        (series.str.lower() != "nan")
    )
