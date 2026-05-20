import pytest
import pandas as pd
from config import GEO_FILTER_FIELD, GEO_FILTER_VALUE, EVENTS_CSV, DATE_MAX, DATE_NOW


# Fixture pour les données d'événements simulées
@pytest.fixture
def df():
    """Charge le fichier events.csv généér par fetch_events.py"""
    df = pd.read_csv(EVENTS_CSV, encoding="utf-8-sig", parse_dates=["firstdate_begin", "lastdate_end"])
    # Convertir les dates en UTC pour cohérence avec les timestamps de config.py
    df["firstdate_begin"] = pd.to_datetime(df["firstdate_begin"], utc=True)
    df["lastdate_end"] = pd.to_datetime(df["lastdate_end"], utc=True)
    return df

# Tests
def test_fichier_non_vide(df):
    """Vérifie que le jeu de données contient des événements"""
    assert len(df) > 0, "Le fichier events.csv est vide"

def test_colonnes_presentes(df):
    """Les colonnes essentielles doivent être présentes dans le dataFrame"""
    colonnes_requises = [
        "uid", "title_fr", "description_fr", "longdescription_fr",
        "firstdate_begin", "lastdate_end", "location_name",
        "location_city", "location_department", "location_region",
        "location_address", "conditions_fr", "keywords_fr"
    ]
    for col in colonnes_requises:
        assert col in df.columns, f"La colonne {col} est absente du DataFrame"

def test_pas_de_titre_manquant(df):
    """Aucun événement ne doit avoir un titre manquant"""
    assert df["title_fr"].isnull().sum() == 0, "Des événements ont un titre manquant"

def test_pas_de_description_manquante(df):
    """Aucun événement ne doit avoir une description manquante"""
    assert df["description_fr"].isnull().sum() == 0, "Des événements ont une description manquante"

def test_pas_de_ville_manquante(df):
    """Aucun événement ne doit avoir une ville manquante (pour le filtrage géographique)"""
    assert df["location_city"].isnull().sum() == 0, f"{df['location_city'].isnull().sum()} événements ont une ville manquante"

def test_pas_de_doublons(df):
    """Aucun événement ne doit être dupliqué (basé sur l'uid)"""
    assert df["uid"].duplicated().sum() == 0, "Il y a des événements dupliqués dans le DataFrame"

def test_filtre_geographique(df):
    """Tous les événements doivent être situés dans la zone géographique spécifiée (ex: Gironde)"""
    invalides = df[df[GEO_FILTER_FIELD] != GEO_FILTER_VALUE]
    assert len(invalides) == 0, f"{len(invalides)} événements hors {GEO_FILTER_VALUE} trouvés"

def test_filtre_temporel(df):
    """Tous les événements doivent dater de moins d'un an"""
    date_now = pd.Timestamp(DATE_NOW).tz_localize("UTC")
    date_max = pd.Timestamp(DATE_MAX).tz_localize("UTC")
    invalides = df[(df["lastdate_end"] < date_now) | (df["lastdate_end"] > date_max)]
    assert len(invalides) == 0, f"{len(invalides)} événements datant de plus d'un an trouvés"

def test_dates_valides(df):
    """Les dates ne doivent pas être NaT après conversion"""
    assert df["firstdate_begin"].isnull().sum() == 0, "Des événements ont une date de début manquante"
    assert df["lastdate_end"].isnull().sum() == 0, "Des événements ont une date de fin manquante"