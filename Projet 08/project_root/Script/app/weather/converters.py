import pandas as pd

def normalize_column_names(df):
	df.columns = (
		df.columns
		.str.lower()
		.str.replace(" ", "_")
		.str.replace(".", "", regex=False)
	)

	return df



def extract_numeric_value(series):
	"""
	Extrait la partie numérique d'une chaîne de caractères contenant une unité.
	"""
	return (
		series
		.astype(str)
		.str.replace(",", ".")
		.str.extract(r"([-+]?\d*\.?\d+)")[0]
		.astype(float)
	)


def fahrenheit_to_celsius(series):
	return (series - 32) * 5.0 / 9.0


def mph_to_kmh(series):
	return series * 1.60934


def inhg_to_hpa(series):
	return series * 33.8639


def inch_to_mm(series):
	return series * 25.4



def degrees_to_cardinal(degree):
	if pd.isnull(degree):
		return None

	dirs = [
		"N","NNE","NE","ENE","E","ESE","SE","SSE",
        "S","SSW","SW","WSW","W","WNW","NW","NNW"
    ]

	ix = int((float(degree) + 11.25) / 22.5)
	return dirs[ix % 16]