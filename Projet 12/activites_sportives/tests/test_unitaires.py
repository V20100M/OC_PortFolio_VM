"""
test_unitaires.py
------------------
Tests unitaires sur les fonctions pures du projet (pas de DB, pas de reseau).
Complementaire aux validations Great Expectations (utils/data_quality.py),
qui valident la donnee a l'execution plutot que la logique du code.

Usage :
  pip install pytest
  pytest tests/
"""

from datetime import date, datetime

import pandas as pd
import pytest

from utils.config import SEUILS, OSRM_PROFILES
from utils.helpers import is_sport_valide
from utils.strava_etl import parse_activity_and_comments
from utils.strava_generation import (
    normalize_sport,
    resolve_sport_rules,
    generate_activity_metrics,
)
from scripts.import_excel import excel_date_to_python, normalize_address


# ---------------------------------------------------------------------------
# utils/strava_generation.py
# ---------------------------------------------------------------------------
class TestNormalizeSport:

    def test_strips_accents_and_case(self):
        assert normalize_sport("Vélo") == "velo"
        assert normalize_sport("  RUNNING  ") == "running"
        assert normalize_sport("Randonnée") == "randonnee"


class TestResolveSportRules:

    def test_exact_match(self):
        assert resolve_sport_rules("velo")["avg_watt"] == (80, 180)

    def test_accent_insensitive_exact_match(self):
        assert resolve_sport_rules("Course À Pied") == resolve_sport_rules("running")

    def test_partial_match_fallback(self):
        # "football" est une sous-chaine de "footballeur"
        assert resolve_sport_rules("footballeur") == resolve_sport_rules("football")

    def test_unknown_sport_uses_default_rules(self):
        rules = resolve_sport_rules("Footing")
        assert rules == {
            "distance": None,
            "moving_time": (30, 120),
            "avg_speed_kmh": None,
            "avg_watt": None,
            "max_watt": None,
        }


class TestGenerateActivityMetrics:

    def test_sport_avec_vitesse_calcule_distance_et_watts(self):
        for _ in range(20):
            (distance, moving_time_sec, elapsed_time_sec,
             avg_speed, max_speed, avg_watt, max_watt) = generate_activity_metrics("velo")

            assert 30 * 60 <= moving_time_sec <= 150 * 60
            assert moving_time_sec <= elapsed_time_sec <= moving_time_sec + 15 * 60
            assert avg_speed is not None and max_speed is not None
            assert max_speed >= avg_speed
            assert avg_watt is not None and max_watt is not None
            # distance coherente avec vitesse * temps, a l'arrondi 2 decimales pres
            # (avg_speed est arrondi pour le stockage, distance est calculee avant arrondi)
            assert abs(distance - avg_speed * moving_time_sec) < 50

    def test_sport_sans_vitesse_ni_watts(self):
        for _ in range(20):
            (distance, moving_time_sec, elapsed_time_sec,
             avg_speed, max_speed, avg_watt, max_watt) = generate_activity_metrics("football")

            assert 60 * 60 <= moving_time_sec <= 90 * 60
            assert distance is None
            assert avg_speed is None and max_speed is None
            assert avg_watt is None and max_watt is None

    def test_sport_avec_plage_de_distance_fixe(self):
        # voile : pas de vitesse, distance tiree dans une plage fixe (5000-40000 m)
        for _ in range(20):
            distance, *_ = generate_activity_metrics("voile")
            assert 5000 <= distance <= 40000


# ---------------------------------------------------------------------------
# utils/strava_etl.py
# ---------------------------------------------------------------------------
class TestParseActivityAndComments:

    def _activity_json(self, **overrides):
        base = {
            "id": 123456789,
            "athlete": {"id": 654321},
            "sport_type": "Running",
            "elapsed_time": 1800,
            "moving_time": 1700,
            "start_date": "2024-01-01T08:00:00Z",
            "_end_date": "2024-01-01T08:30:00Z",
            "distance": 5000,
            "average_speed": 2.5,
            "max_speed": 3.0,
            "average_watts": None,
            "max_watts": None,
        }
        base.update(overrides)
        return base

    def test_parse_activite_complete(self):
        activity_data, comments_data = parse_activity_and_comments(self._activity_json(), [])

        assert activity_data == (
            123456789, 654321,
            datetime(2024, 1, 1, 8, 0), datetime(2024, 1, 1, 8, 30),
            "Running",
            5000.0, 1700, 1800,
            2.5, 3.0, None, None,
        )
        assert comments_data == []

    def test_champ_obligatoire_manquant_leve_value_error(self):
        activity = self._activity_json()
        del activity["athlete"]
        with pytest.raises(ValueError):
            parse_activity_and_comments(activity, [])

    def test_end_date_calculee_si_absente(self):
        activity = self._activity_json()
        del activity["_end_date"]
        activity_data, _ = parse_activity_and_comments(activity, [])
        start_dt, end_dt = activity_data[2], activity_data[3]
        assert (end_dt - start_dt).total_seconds() == activity["elapsed_time"]

    def test_distance_zero_convertie_en_none(self):
        # sports sans deplacement (football, judo...) : distance = 0 dans le JSON simule
        activity = self._activity_json(distance=0, average_speed=0, max_speed=0)
        activity_data, _ = parse_activity_and_comments(activity, [])
        distance, avg_speed, max_speed = activity_data[5], activity_data[8], activity_data[9]
        assert distance is None
        assert avg_speed is None
        assert max_speed is None

    def test_commentaires_malformes_sont_ignores(self):
        comments = [
            {"id": 1, "text": "bravo", "athlete": {"firstname": "A", "lastname": "B"},
             "created_at": "2024-01-01T09:00:00Z"},
            {"text": "pas d'id, doit etre ignore"},
        ]
        _, comments_data = parse_activity_and_comments(self._activity_json(), comments)
        assert len(comments_data) == 1
        assert comments_data[0][0] == 1
        assert comments_data[0][2] == "bravo"
        assert comments_data[0][3] == "A B"


# ---------------------------------------------------------------------------
# utils/helpers.py
# ---------------------------------------------------------------------------
class TestIsSportValide:

    def test_exclut_nan_vide_espaces_et_nan_texte(self):
        series = pd.Series([None, "", "   ", "nan", "NaN", "Football", "Tennis "])
        assert is_sport_valide(series).tolist() == [
            False, False, False, False, False, True, True,
        ]


# ---------------------------------------------------------------------------
# scripts/import_excel.py
# ---------------------------------------------------------------------------
class TestExcelDateToPython:

    def test_valeur_absente_retourne_none(self):
        assert excel_date_to_python(None) is None
        assert excel_date_to_python(float("nan")) is None

    def test_objet_date_existant_est_conserve(self):
        assert excel_date_to_python(date(2020, 5, 14)) == date(2020, 5, 14)

    def test_objet_datetime_conserve_sa_composante_horaire(self):
        # Bug latent : isinstance(value, date) est vrai aussi pour un datetime
        # (sous-classe de date), donc la branche "value.date()" ne s'execute
        # jamais et l'heure n'est pas retiree. Documente ici pour eviter une
        # regression silencieuse si ce comportement est corrige plus tard.
        result = excel_date_to_python(datetime(2020, 5, 14, 10, 30))
        assert result == datetime(2020, 5, 14, 10, 30)

    def test_chaine_texte_format_iso_et_francais(self):
        assert excel_date_to_python("2020-05-14") == date(2020, 5, 14)
        assert excel_date_to_python("14/05/2020") == date(2020, 5, 14)

    def test_serial_excel_avant_bug_1900(self):
        # serial 1 = 1er jour de l'epoque Excel = 1900-01-01
        assert excel_date_to_python(1) == date(1900, 1, 1)

    def test_serial_excel_apres_bug_1900(self):
        # serial 61 = 1900-03-01 (Excel compte a tort un 29 fevrier 1900)
        assert excel_date_to_python(61) == date(1900, 3, 1)
        assert excel_date_to_python("61") == date(1900, 3, 1)

    def test_chaine_non_convertible_retourne_none(self):
        assert excel_date_to_python("pas une date") is None


class TestNormalizeAddress:

    def test_remplace_les_abreviations_courantes(self):
        assert normalize_address("12 Bd de la Republique") == "12 Boulevard de la Republique"
        assert normalize_address("5 Av. Foch") == "5 Avenue Foch"
        assert normalize_address("3 Chem des Vignes") == "3 Chemin des Vignes"

    def test_collapse_espaces_multiples(self):
        assert normalize_address("12   Rue   des  Fleurs") == "12 Rue des Fleurs"

    def test_valeur_non_string_est_retournee_telle_quelle(self):
        assert normalize_address(None) is None
        assert normalize_address(float("nan")) != normalize_address(float("nan"))  # nan != nan


# ---------------------------------------------------------------------------
# utils/config.py — coherence avec les regles documentees dans le README
# ---------------------------------------------------------------------------
class TestSeuilsEligibilite:

    def test_seuils_documentes(self):
        assert SEUILS["Marche/running"] == 15.0
        assert SEUILS["Vélo/Trottinette/Autres"] == 25.0

    def test_profils_osrm_associes(self):
        assert OSRM_PROFILES["Marche/running"] == "foot"
        assert OSRM_PROFILES["Vélo/Trottinette/Autres"] == "bike"
