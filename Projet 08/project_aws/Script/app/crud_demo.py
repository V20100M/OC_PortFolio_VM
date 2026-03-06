import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

# -----------------------
# LOGGING
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------
# CONFIG
# -----------------------
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "weather_db")

COL_STATIONS = "stations"
COL_WEATHER = "weather_measurements"


def utc_now() -> datetime:
    # datetime.utcnow() est déprécié -> on utilise timezone-aware
    return datetime.now(timezone.utc)


def get_db():
    client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
    return client[MONGO_DB]


def get_collection(name: str) -> Collection:
    return get_db()[name]


# -----------------------
# STATIONS CRUD
# -----------------------
def create_station(station: Dict[str, Any]) -> bool:
    """
    CREATE station (id_station unique)
    """
    col = get_collection(COL_STATIONS)
    now = utc_now()
    station = {**station, "created_at": now, "updated_at": now}

    try:
        col.insert_one(station)
        logger.info(f"Station créée: {station.get('id_station')}")
        return True
    except DuplicateKeyError:
        logger.warning(f"Station déjà existante: {station.get('id_station')}")
        return False


def get_station(id_station: str) -> Optional[Dict[str, Any]]:
    """
    READ station
    """
    col = get_collection(COL_STATIONS)
    return col.find_one({"id_station": id_station}, {"_id": 0})


def update_station(id_station: str, updates: Dict[str, Any]) -> int:
    """
    UPDATE station (partiel)
    """
    col = get_collection(COL_STATIONS)
    updates = {**updates, "updated_at": utc_now()}
    res = col.update_one({"id_station": id_station}, {"$set": updates})
    logger.info(f"Station update matched={res.matched_count} modified={res.modified_count}")
    return res.modified_count


def delete_station(id_station: str) -> int:
    """
    DELETE station
    """
    col = get_collection(COL_STATIONS)
    res = col.delete_one({"id_station": id_station})
    logger.info(f"Station supprimée deleted={res.deleted_count}")
    return res.deleted_count


# -----------------------
# WEATHER CRUD
# -----------------------
def create_weather_measurement(id_station: str, dh_utc: datetime, weather: Dict[str, Any]) -> bool:
    """
    CREATE weather measurement (unique index sur id_station + dh_utc)
    """
    col = get_collection(COL_WEATHER)
    now = utc_now()

    doc = {
        "id_station": str(id_station),
        "dh_utc": dh_utc,
        "weather": weather,
        "created_at": now,
        "updated_at": now
    }

    try:
        col.insert_one(doc)
        logger.info(f"Mesure créée: {id_station} @ {dh_utc.isoformat()}")
        return True
    except DuplicateKeyError:
        logger.warning(f"Mesure déjà existante: {id_station} @ {dh_utc.isoformat()}")
        return False


def get_weather_measurement(id_station: str, dh_utc: datetime) -> Optional[Dict[str, Any]]:
    """
    READ 1 measurement
    """
    col = get_collection(COL_WEATHER)
    return col.find_one({"id_station": str(id_station), "dh_utc": dh_utc}, {"_id": 0})


def list_weather_by_station(id_station: str, limit: int = 5, newest_first: bool = True) -> List[Dict[str, Any]]:
    """
    READ many measurements for a station
    """
    col = get_collection(COL_WEATHER)
    sort_dir = -1 if newest_first else 1
    cursor = (
        col.find({"id_station": str(id_station)}, {"_id": 0})
        .sort("dh_utc", sort_dir)
        .limit(limit)
    )
    return list(cursor)


def update_weather_measurement(id_station: str, dh_utc: datetime, weather_updates: Dict[str, Any]) -> int:
    """
    UPDATE measurement -> met à jour seulement des champs dans weather.*
    Exemple: {"temperature": 12.3}
    """
    col = get_collection(COL_WEATHER)

    set_ops = {f"weather.{k}": v for k, v in weather_updates.items()}
    set_ops["updated_at"] = utc_now()

    res = col.update_one({"id_station": str(id_station), "dh_utc": dh_utc}, {"$set": set_ops})
    logger.info(f"Météo update matched={res.matched_count} modified={res.modified_count}")
    return res.modified_count


def delete_weather_measurement(id_station: str, dh_utc: datetime) -> int:
    """
    DELETE measurement
    """
    col = get_collection(COL_WEATHER)
    res = col.delete_one({"id_station": str(id_station), "dh_utc": dh_utc})
    logger.info(f"Mesure supprimée deleted={res.deleted_count}")
    return res.deleted_count


# -----------------------
# DEMO EXEC
# -----------------------
def demo():
    # 1) CREATE station
    station_demo = {
        "id_station": "DEMO001",
        "station_name": "Station Demo",
        "location": {"city": "DemoCity", "latitude": 0.0, "longitude": 0.0, "elevation": 0},
        "station_type": "static",
        "source": "demo",
        "metadata": {}
    }
    create_station(station_demo)

    # 2) READ station
    st = get_station("DEMO001")
    logger.info(f"READ station: {st}")

    # 3) UPDATE station
    update_station("DEMO001", {"station_name": "Station Demo Updated"})

    # 4) CREATE weather measurement
    dh = datetime(2024, 10, 1, 0, 4, 0, tzinfo=timezone.utc)
    weather_doc = {
        "temperature": 18.3,
        "pression": 1002.4,
        "humidite": 57.0,
        "point_de_rosee": 9.7,
        "vent_direction": "NW",
        "vent_moyen": 2.1,
        "vent_rafales": 8.9,
        "pluie_1h": 0.0,
        "pluie_3h": 0.0,
        "solar": 246.0,
        "uv": 2.0
    }
    create_weather_measurement("DEMO001", dh, weather_doc)

    # 5) READ measurement
    m = get_weather_measurement("DEMO001", dh)
    logger.info(f"READ measurement: {m}")

    # 6) LIST last measurements
    ms = list_weather_by_station("DEMO001", limit=3)
    logger.info(f"LIST measurements (3): {ms}")

    # 7) UPDATE measurement (ex: temperature)
    update_weather_measurement("DEMO001", dh, {"temperature": 19.1})

    # 8) DELETE measurement
    delete_weather_measurement("DEMO001", dh)

    # 9) DELETE station
    delete_station("DEMO001")


if __name__ == "__main__":
    demo()