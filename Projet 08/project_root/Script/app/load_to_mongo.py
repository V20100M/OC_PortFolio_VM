import os
import logging
import pandas as pd
from datetime import datetime, timezone
import time

from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

#import config as cfg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log_to_mongo.log'),
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)

# Configuration MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "weather_db")

# Connecion à MongoDB
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]



# Initialisation des index pour éviter les doublons
def init_indexes():
	logger.info("Initialisation des index MongoDB.")

	weather = db['weather_measurements']
	stations = db['stations']

	# Index pour weather_measurements
	weather.create_index(
		[("id_station", 1), ("dh_utc", 1)],
		unique=True
	)

	# Index pour stations
	stations.create_index(
		[("id_station", 1)],
		unique=True
	)


# Connexion à MongoDB pour la collection weathers
def get_weather_collection():
	collection = db['weather_measurements']
	return collection


# Connexion à MongoDB pour la collection stations
def get_stations_collection():
	collection = db['stations']
	return collection



# Migration des données des stations vers MongoDB
def migrate_data_stations(stations):
	logger.info("Connexion MongoDB (stations).")
	collection = get_stations_collection()

	#stations = build_stations()

	if not stations:
		logger.warning("Aucune station à migrer.")
		return

	start_time = time.time()
	now = datetime.now(timezone.utc)

	# Préparer les opérations de mise à jour pour éviter les doublons
	operations = []

	for station in stations:
		operations.append(
		 	UpdateOne(
				{"id_station": station["id_station"]},
			 	{
         			"$set": {
						**station,
						"updated_at": now,
					},
		  			"$setOnInsert": {
						"created_at": now,
					}
				},
			 	upsert=True
		 	)
	 	)

	logger.info(f"Nombre de stations à migrer: {len(operations)}")

	try:
		result = collection.bulk_write(operations, ordered=False)

		duration = time.time() - start_time

		logger.info(
	  		f"Migration stations terminée. | "
			f"Insertions: {result.upserted_count} | "
			f"Modifications: {result.modified_count} |"
			f"Temps écoulé: {duration:.2f} secondes"
		)

	except BulkWriteError as e:
		logger.error(f"Erreur d'écriture en masse")
		logger.error(str(e.details))



# Migration des données météo vers MongoDB
def migrate_data_weather(df: pd.DataFrame):
    logger.info("Connexion MongoDB (weather_measurements).")
    collection = get_weather_collection()

    if df.empty:
        logger.warning("Aucune données à migrer.")
        return

	# Conversion datetime MongoDB
    df['dh_utc'] = pd.to_datetime(df['dh_utc'])

    start_time = time.time()
    now = datetime.now(timezone.utc)

	# Préparer les opérations de mise à jour pour éviter les doublons
    operations = []

    for row in df.to_dict("records"):

        operations.append(
		 	UpdateOne(
				{
        			"id_station": row["id_station"],
     				"dh_utc": row["dh_utc"].to_pydatetime()
        		},
			 	{
         			"$set": {
                		"weather": row["weather"],
						"updated_at": now
      				},
      				"$setOnInsert": {
              			"created_at": now
                 	}
			 	},
			 	upsert=True
		 	)
	 	)

    logger.info(f"Nombre de documents à migrer: {len(operations)}")

    try:
        result = collection.bulk_write(operations, ordered=False)

        duration = time.time() - start_time

        logger.info(
      		f"Migration des données terminée. | "
        	f"Insertions: {result.upserted_count} | "
        	f"Modifications: {result.modified_count} | "
        	f"Temps écoulé: {duration:.2f} secondes"
    	)

    except BulkWriteError as e:
        logger.error(f"Erreur d'écriture en masse")
        logger.error(str(e.details))



# Vérification de l'intégrité des données dans MongoDB
def check_integrity():
	logger.info("Vérification de l'intégrité des données dans MongoDB.")

	weather_collection = get_weather_collection()
	stations_collection = get_stations_collection()

	weather_ids = set(weather_collection.distinct("id_station"))
	station_ids = set(stations_collection.distinct("id_station"))

	missing = weather_ids - station_ids

	if missing:
		logger.error(f"{len(missing)} mesures météo sans station correspondante.")
	else:
		logger.info("Toutes les mesures météo ont une station correspondante.")


