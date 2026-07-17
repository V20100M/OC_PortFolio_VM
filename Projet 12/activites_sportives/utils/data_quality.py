"""
data_quality.py
-----------------
Validation de la qualite des donnees via Great Expectations.

Cinq familles de validations :
  - validate_salarie_df / validate_sportpratique_df :
        sur DataFrames pandas, AVANT import (bloquant)
  - validate_salarie_table / validate_sportpratique_table :
        sur tables PostgreSQL, APRES import (bloquant)
  - validate_geocode_coverage / validate_geocode_table :
        couverture et coherence du geocodage (bloquant)
  - validate_strava_table :
        coherence des activites generees (bloquant si donnees presentes)
  - validate_strava_comment_table :
        unicite et non-nullite des commentaires (bloquant si donnees presentes)

Toutes les fonctions retournent un resultat GX ou None (table vide → skip).
"""

import great_expectations as gx
import pandas as pd
from datetime import date

from .config import SEUILS, SPORT_RULES
from .strava_generation import normalize_sport


VALEURS_MOYEN_DEPLACEMENT = [
    "Marche/running",
    "Vélo/Trottinette/Autres",
    "Transports en commun",
    "véhicule thermique/électrique",
]
VALEURS_TYPE_CONTRAT = ["CDI", "CDD"]


def _validate_dataframe(df, suite_name, expectations):
    """Execute une suite d'expectations sur un DataFrame pandas."""
    context = gx.get_context()
    data_source = context.data_sources.add_pandas(f"{suite_name}_source")
    data_asset = data_source.add_dataframe_asset(name=f"{suite_name}_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"{suite_name}_batch")

    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    for exp in expectations:
        suite.add_expectation(exp)

    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


def format_validation_errors(result):
    """Retourne une liste de messages d'erreur lisibles a partir d'un resultat GX."""
    errors = []
    for r in result.results:
        if not r.success:
            exp_type = r.expectation_config.type
            column = r.expectation_config.kwargs.get("column", "")
            unexpected = r.result.get("partial_unexpected_list", [])
            count = r.result.get("unexpected_count", 0)
            errors.append(
                f"{exp_type} [{column}] : {count} valeur(s) invalide(s) -> {unexpected}"
            )
    return errors


# ---------------------------------------------------------------------------
# Validations AVANT import (DataFrames pandas)
# ---------------------------------------------------------------------------
def validate_salarie_df(df):
    """Valide le DataFrame salarie avant insertion en base."""
    df_check = df.copy()

    # Colonnes derivees pour les checks inter-colonnes (4a)
    df_check["annee_naissance"] = pd.to_datetime(
        df_check["date_naissance"], errors="coerce"
    ).dt.year
    df_check["annee_embauche"] = pd.to_datetime(
        df_check["date_embauche"], errors="coerce"
    ).dt.year
    # Les nulls sont déjà capturés par ExpectColumnValuesToNotBeNull ci-dessous
    df_check["embauche_apres_naissance"] = (
        pd.to_datetime(df_check["date_embauche"],  errors="coerce") >
        pd.to_datetime(df_check["date_naissance"], errors="coerce")
    ).fillna(True)

    expectations = [
        gx.expectations.ExpectColumnValuesToBeUnique(column="id_salarie"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="id_salarie"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="nom"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="prenom"),
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="salaire_brut", min_value=0, strict_min=True
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="type_contrat", value_set=VALEURS_TYPE_CONTRAT
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="moyen_deplacement", value_set=VALEURS_MOYEN_DEPLACEMENT
        ),
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="jours_cp", min_value=0
        ),
        # 4a — Plage d'années cohérente avec une population salariée active
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="annee_naissance", min_value=1940, max_value=2005
        ),
        # 4a — date_embauche ne peut pas être dans le futur
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="annee_embauche", max_value=date.today().year
        ),
        # 4a — On doit être embauché après sa naissance
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="embauche_apres_naissance", value_set=[True]
        ),
    ]
    return _validate_dataframe(df_check, "salarie_avant_import", expectations)


def validate_sportpratique_df(df, salarie_ids):
    """
    Valide le DataFrame sportpratique avant insertion.
    salarie_ids : set des id_salarie valides (issus du DataFrame salarie)
    pour verifier l'integrite referentielle avant insertion en base.
    """
    df_check = df.copy()
    df_check["id_salarie_valide"] = df_check["id_salarie"].isin(salarie_ids)
    # 4d — Normalisation accent/casse pour comparer aux clés de SPORT_RULES
    df_check["sport_normalise"] = df_check["pratique_sport"].apply(normalize_sport)

    expectations = [
        gx.expectations.ExpectColumnValuesToNotBeNull(column="pratique_sport"),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="id_salarie_valide", value_set=[True]
        ),
        # 4d — Le sport doit être reconnu par le moteur de génération
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="sport_normalise",
            value_set=list(SPORT_RULES.keys()),
        ),
    ]
    return _validate_dataframe(df_check, "sportpratique_avant_import", expectations)


# ---------------------------------------------------------------------------
# Validations APRES import (tables PostgreSQL, via pandas.read_sql)
# ---------------------------------------------------------------------------
def validate_salarie_table(engine):
    """Valide la table salarie apres insertion en base."""
    df = pd.read_sql("SELECT * FROM salarie;", engine)
    return validate_salarie_df(df)


def validate_sportpratique_table(engine):
    """Valide la table sportpratique apres insertion en base."""
    df_salarie = pd.read_sql("SELECT id_salarie FROM salarie;", engine)
    salarie_ids = set(df_salarie["id_salarie"])

    df_sport = pd.read_sql("SELECT * FROM sportpratique;", engine)
    return validate_sportpratique_df(df_sport, salarie_ids)


# ---------------------------------------------------------------------------
# Validations geocodage (couverture + coherence)
# ---------------------------------------------------------------------------
def validate_geocode_coverage(engine):
    """
    Verifie que tous les salaries ont une entree dans salarie_geocode.
    (4c — couverture complete : aucun salarie ne doit avoir ete saute)
    """
    total_salaries = int(
        pd.read_sql("SELECT COUNT(*) AS cnt FROM salarie;", engine).iloc[0]["cnt"]
    )
    df = pd.read_sql("SELECT id_salarie FROM salarie_geocode;", engine)
    expectations = [
        gx.expectations.ExpectTableRowCountToEqual(value=total_salaries)
    ]
    return _validate_dataframe(df, "geocode_couverture", expectations)


def validate_geocode_table(engine):
    """
    Valide la coherence distance_km / seuil / eligible_prime
    et les coordonnees GPS dans salarie_geocode,
    en jointure avec salarie pour le moyen_deplacement.
    """
    df = pd.read_sql("""
        SELECT
            g.id_salarie,
            s.moyen_deplacement,
            g.distance_km,
            g.eligible_prime,
            g.geocode_ok,
            g.latitude,
            g.longitude
        FROM salarie_geocode g
        JOIN salarie s ON g.id_salarie = s.id_salarie
        WHERE g.geocode_ok = TRUE AND g.distance_km IS NOT NULL;
    """, engine)

    if df.empty:
        return None  # aucune ligne geocodee avec succes, rien a valider

    df["seuil"] = df["moyen_deplacement"].map(SEUILS)
    df["eligible_attendu"] = df["distance_km"] <= df["seuil"]

    expectations = [
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="distance_km", min_value=0
        ),
        gx.expectations.ExpectColumnPairValuesToBeEqual(
            column_A="eligible_prime", column_B="eligible_attendu"
        ),
        # 4b — Bounding box France metropolitaine
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="latitude", min_value=41.0, max_value=51.5
        ),
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="longitude", min_value=-5.5, max_value=9.5
        ),
    ]
    return _validate_dataframe(df, "geocode_apres_import", expectations)


# ---------------------------------------------------------------------------
# Validation post-generation Strava (4e)
# ---------------------------------------------------------------------------
def validate_strava_table(engine):
    """
    Valide la table strava apres generation des activites.
    Retourne None si la table est vide (pipeline pas encore execute jusqu'a cette etape).
    """
    df = pd.read_sql("SELECT * FROM strava;", engine)
    if df.empty:
        return None

    df_check = df.copy()

    # Coherence temporelle : elapsed >= moving, end > start
    df_check["elapsed_gte_moving"] = (
        df_check["elapsed_time"] >= df_check["moving_time"]
    )
    df_check["end_apres_start"] = (
        pd.to_datetime(df_check["end_date"]) > pd.to_datetime(df_check["start_date"])
    ).fillna(True)  # les nulls sont capturés par ExpectColumnValuesToNotBeNull

    # Coherence watts : avg_watt <= max_watt (uniquement si les deux sont presents)
    df_check["watt_coherent"] = True
    watt_mask = df_check["avg_watt"].notna() & df_check["max_watt"].notna()
    if watt_mask.any():
        df_check.loc[watt_mask, "watt_coherent"] = (
            df_check.loc[watt_mask, "avg_watt"] <= df_check.loc[watt_mask, "max_watt"]
        )

    expectations = [
        gx.expectations.ExpectColumnValuesToBeUnique(column="id_strava"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="sport_type"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="start_date"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="end_date"),
        gx.expectations.ExpectColumnValuesToBeBetween(column="moving_time",  min_value=1),
        gx.expectations.ExpectColumnValuesToBeBetween(column="elapsed_time", min_value=1),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="elapsed_gte_moving", value_set=[True]
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="end_apres_start", value_set=[True]
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="watt_coherent", value_set=[True]
        ),
        # Distance et vitesses positives quand presentes (les nulls sont ignores par GX)
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="distance",  min_value=0, strict_min=True
        ),
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="avg_speed", min_value=0, strict_min=True
        ),
        gx.expectations.ExpectColumnValuesToBeBetween(column="avg_watt", min_value=0),
        gx.expectations.ExpectColumnValuesToBeBetween(column="max_watt", min_value=0),
    ]
    return _validate_dataframe(df_check, "strava_apres_generation", expectations)


def validate_strava_comment_table(engine):
    """
    Valide la table strava_comment apres generation des activites.
    Retourne None si la table est vide.
    """
    df = pd.read_sql("SELECT * FROM strava_comment;", engine)
    if df.empty:
        return None

    expectations = [
        gx.expectations.ExpectColumnValuesToBeUnique(column="id_comment"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="id_comment"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="id_strava"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="created_at"),
    ]
    return _validate_dataframe(df, "strava_comment_apres_generation", expectations)
