import config as cfg
import logging
import pandas as pd

from data_io.s3_reader import list_s3_jsonl_files, read_json_from_s3

logger = logging.getLogger(__name__)

def build_stations():
	logger.info("build_stations appelé")

 	# Stations Weather Underground
	stations_wu = [
		{
			"id_station": "IICHTE19",
			"station_name": "WeerstationBS",
			"location": {
				"latitude": 51.092,
				"longitude": 2.999,
				"elevation": 15,
				"city": "Ichtegem",
			},
			"station_type": "static",
			"source": "weather_underground",
			"metadata": {
				"hardware": "other",
				"software": "EasyWeatherV1.6.6",
				"license_source": "",
				"url": "https://easyweathertool.com/",
				"url_source": "https://www.wunderground.com/",
				"metadonnees": "https://www.wunderground.com/weather/be/ichtegem"
			}


		},
		{
			"id_station": "ILAMAD25",
			"station_name": "La Madeleine",
			"location": {
				"latitude": 50.659,
				"longitude": 3.07,
				"elevation": 23,
				"city": "La Madeleine",
			},
			"station_type": "static",
			"source": "weather_underground",
			"metadata": {
				"hardware": "other",
				"software": "EasyWeatherPro_V5.1.6",
				"license_source": "",
				"url": "https://easyweathertool.com/",
				"url_source": "https://www.wunderground.com/",
				"metadonnees": "https://www.wunderground.com/weather/fr/la-madeleine"
			}
		}
	]

	# Stations InfoClimat
	infoclimat_prefix = cfg.RAWS_PATH["infoclimat"]
	infoclimat_files = list_s3_jsonl_files(infoclimat_prefix)

	if not infoclimat_files:
		raise ValueError(f"Aucun fichier JSONL trouvé pour la source infoclimat avec le préfixe {infoclimat_prefix}")

	# On prend le dernier fichier (le plus récent)
	infoclimat_path = infoclimat_files[-1]
	logger.info(f"Lecture du fichier InfoClimat : {infoclimat_path}")

	df = read_json_from_s3(infoclimat_path)
	airbyte_df = df["_airbyte_data"].apply(pd.Series)

	stations_list = airbyte_df["stations"].iloc[0]
	stations_ic_df = pd.DataFrame(stations_list)

	stations_infoclimat = []

	for _, row in stations_ic_df.iterrows():
		license_info = row.get("license", {})
		stations_infoclimat.append(
			{
                "id_station": row.get("id"),
                "station_name": row.get("name"),
                "location": {
	                "latitude": row.get("latitude"),
	                "longitude": row.get("longitude"),
	                "elevation": row.get("elevation"),
	                "city": row.get("name"),
                },
                "station_type": row.get("type"),
                "source": "infoclimat",
                "metadata": {
	                "hardware": None,
	                "software": None,
	                "license_source": license_info.get("license"),
	                "url": license_info.get("url"),
	                "url_source": license_info.get("source"),
	                "metadonnees": license_info.get("metadonnees")
                }
			}
		)

	stations = stations_wu + stations_infoclimat
	logger.info(f"{len(stations)} stations construites au total ({len(stations_wu)} de Weather Underground et {len(stations_infoclimat)} d'InfoClimat)")

	return stations