import pandas as pd
import logging

from data_io.s3_reader import read_json_from_s3
from weather.converters import normalize_column_names, extract_numeric_value, fahrenheit_to_celsius, mph_to_kmh, inhg_to_hpa, inch_to_mm, degrees_to_cardinal
from quality.validators import validate_weather_data

logger = logging.getLogger(__name__)


EN_TO_FR = {
	"pressure": "pression",
	"humidity": "humidite",
	"dew_point": "point_de_rosee",
	"temperature": "temperature",
	"wind": "vent_direction",
	"speed": "vent_moyen",
	"gust": "vent_rafales",
	"precip_rate": "pluie_1h",
	"precip_accum": "pluie_3h",
	"solar": "solar",
	"uv": "uv"
}

NUMERIC_FIELDS = [
    "pressure", "speed", "gust",
    "precip_rate", "precip_accum",
    "humidity", "dew_point",
    "temperature", "solar", "uv",
    "pression", "vent_moyen", "vent_rafales",
    "pluie_1h", "pluie_3h",
    "humidite", "point_de_rosee"
]

FINAL_WEATHER_COLUMNS = [
	"temperature",
	"pression",
	"humidite",
	"point_de_rosee",
	"vent_direction",
	"vent_moyen",
	"vent_rafales",
	"pluie_1h",
	"pluie_3h",
	"solar",
	"uv"
]



def transform_weather(path, stations):

	logger.info(f"Transformation démarrée pour {path}")

	# Récupération de la source et de l'ids_station
	id_station, source = resolve_station_from_path(path, stations)

	if source is None:
		logger.error(f"Source inconnue pour {path}")
		raise ValueError("Source inconnue")

	# Lecture du fichier raw depuis s3
	df = read_json_from_s3(path)

	# Extraction des données Airbyte et normalisation des noms de colonnes
	weather_df = df["_airbyte_data"].apply(pd.Series)
	weather_df = normalize_column_names(weather_df)


	# Cas InfoClimat
	if source == "infoclimat":

		if "hourly" in weather_df.columns:
			hourly_obj = weather_df["hourly"].iloc[0]

			rows = []
			for station_id, measures in hourly_obj.items():
				if station_id == "_params":
					continue
				if isinstance(measures, list):
					rows.extend(measures)

			weather_df = pd.DataFrame(rows)
			weather_df = normalize_column_names(weather_df)

		# Conversion degrés en cardinal
		if "vent_direction" in weather_df.columns:
			weather_df["vent_direction"] = weather_df["vent_direction"].apply(degrees_to_cardinal)

		weather_df["dh_utc"] = pd.to_datetime(weather_df["dh_utc"])

	# Cas Weather Underground
	elif source == "weather_underground":
		# Conversion des valeurs numériques (suppression des unités)
		weather_df = apply_numeric_conversion(weather_df)

		# Conversion vers unités standards (à n'appliquer qu'aux données de Weather Underground)
		weather_df = apply_unit_conversion(weather_df)

		# Reconstruction datetime
		weather_df["dh_utc"] = pd.to_datetime(
			weather_df["dh_utc"],
			errors="coerce"
		)

		# Détermination de l'id_station puis ajout
		weather_df["id_station"] = id_station


	# Harmonisation
	weather_df = weather_df.rename(columns=EN_TO_FR)
	weather_df = apply_numeric_conversion(weather_df)

	# On protège id_station du changement de type
	if "id_station" in weather_df.columns:
		weather_df["id_station"] = weather_df["id_station"].astype(str)
	else:
		logger.error("Colonne id_station absente après transformation")
		weather_df["id_station"] = None

	num_cols = weather_df.select_dtypes(include="number").columns
	#num_cols = [col for col in num_cols if col != "id_station"]
	if len(num_cols) > 0:
		weather_df[num_cols] = weather_df[num_cols].astype(float).round(1)

	# Validation qualité
	clean_data, rejected_data, report = validate_weather_data(weather_df)
	clean_data = clean_data.copy()

	# On veut empêcher les doublons
	before = len(clean_data)

	clean_data = clean_data.drop_duplicates(
		subset=["id_station", "dh_utc"],
		keep="last"
	)

	duplicates_removed = before - len(clean_data)
	report["duplicates_removed"] = duplicates_removed

	# Préparation pour MongoDB
	for col in FINAL_WEATHER_COLUMNS:
		if col not in clean_data.columns:
			clean_data[col] = None

	clean_data["weather"] = clean_data[FINAL_WEATHER_COLUMNS].to_dict(orient="records")

	clean_data = clean_data[[
		"id_station",
		"dh_utc",
		"weather"
	]]

	logger.info(
		f"Transformation terminée | "
		f"Total: {report['total_rows']} | "
		f"Valides: {report['valid_rows']} | "
		f"Rejetées: {report['rejected_rows']} | "
		f"Doublons supprimés: {duplicates_removed}"
	)

	return clean_data, rejected_data, report




def resolve_station_from_path(path, stations):

	path_normalized = path.lower().replace(" ", "")

	# On détermine la source
	if "weather_underground" in path_normalized:
		source = "weather_underground"
	elif "infoclimat" in path_normalized:
		source = "infoclimat"
	else:
		return None, None

	# Résolution station
	if source == "weather_underground":
		# Mapping ville id_station
		wu_stations = {
			s["location"]["city"].lower().replace(" ", ""): s["id_station"]
			for s in stations
			if s.get("source") == "weather_underground"
			and s.get("location", {}).get("city")
		}

		for city_normalized, station_id in wu_stations.items():
			if city_normalized in path_normalized:
				return station_id, source

		# Source trouvée mais station non trouvée
		return None, source

	# Cas InfoClimat (on a déjà l'id_station)
	return None, source




def apply_numeric_conversion(weather_df):

	# Convertit uniquement les colonnes numériques en extrayant la valeur numérique des chaînes
	for col in NUMERIC_FIELDS:
		if col in weather_df.columns:
			weather_df[col] = extract_numeric_value(weather_df[col])

	return weather_df




def apply_unit_conversion(weather_df):

	# Convertit les valeurs d'une unité au unités internationales
	if "pressure" in weather_df:
		weather_df["pressure"] = inhg_to_hpa(weather_df["pressure"])

	if "speed" in weather_df:
		weather_df["speed"] = mph_to_kmh(weather_df["speed"])
	if "gust" in weather_df:
		weather_df["gust"] = mph_to_kmh(weather_df["gust"])

	if "precip_rate" in weather_df:
		weather_df["precip_rate"] = inch_to_mm(weather_df["precip_rate"])
	if "precip_accum" in weather_df:
		weather_df["precip_accum"] = inch_to_mm(weather_df["precip_accum"])

	if "dew_point" in weather_df:
		weather_df["dew_point"] = fahrenheit_to_celsius(weather_df["dew_point"])
	if "temperature" in weather_df:
		weather_df["temperature"] = fahrenheit_to_celsius(weather_df["temperature"])

	return weather_df