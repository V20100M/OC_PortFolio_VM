import pandas as pd

# Validation numérique stricte
NUMERIC_FIELDS = [
	"temperature",
	"pression",
	"humidite",
	"point_de_rosee",
	"vent_moyen",
	"vent_rafales",
	"pluie_1h",
	"pluie_3h",
	"solar",
	"uv"
]

# Validation de la qualité des données météorologiques
def validate_weather_data(weather_df):

	# Sépare les données valides des données rejetées
	df = weather_df.copy()
	df["reject_reason"] = None

	missing_columns = []

	# Validation de la présence des colonnes essentielles
	if "id_station" not in df.columns:
		missing_columns.append("id_station")

	if "dh_utc" not in df.columns:
		missing_columns.append("dh_utc")

	if missing_columns:
		df["reject_reason"] = (f"missing_required_columns:{', '.join(missing_columns)}")
		clean_data = df.iloc[0:0].copy()  # DataFrame vide pour les données valides
		rejected_data = df.copy()
		report = {
			"total_rows": len(df),
			"valid_rows": 0,
			"rejected_rows": len(df),
			"error": 1.0,
			"missing_columns": missing_columns
		}
		return clean_data, rejected_data, report

	# Règles de validation
	mask_is = df["id_station"].isnull()
	df.loc[mask_is & df["reject_reason"].isnull(), "reject_reason"] = "invalid_id_station"

	mask_id = df["dh_utc"].isnull()
	df.loc[mask_id & df["reject_reason"].isnull(), "reject_reason"] = "invalid_datetime"


	for col in NUMERIC_FIELDS:
		if col in df.columns:

			converted = pd.to_numeric(df[col], errors="coerce")
			invalid_numeric = converted.isnull() & df[col].notnull()
			df.loc[invalid_numeric & df["reject_reason"].isnull(), "reject_reason"] = f"invalid_numeric_value_{col}"

			if col == "temperature":
				incoherent_temp = (converted > 65) & df["reject_reason"].isnull()
				df.loc[incoherent_temp, "reject_reason"] = "incoherent_temperature_value"

	# Lignes valides donc sans rejet
	clean_data = df[df["reject_reason"].isnull()].copy()

	# Lignes rejetées
	rejected_data = df[df["reject_reason"].notnull()].copy()

	total_rows = len(df)
	valid_rows = len(clean_data)
	rejected_rows = len(rejected_data)
	report = {
		"total_rows": total_rows,
		"valid_rows": valid_rows,
		"rejected_rows": rejected_rows,
		"error": rejected_rows / total_rows if total_rows > 0 else 0.0
	}


	return clean_data, rejected_data, report