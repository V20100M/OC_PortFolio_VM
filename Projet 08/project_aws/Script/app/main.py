import config as cfg
import pandas as pd
import logging
import time

from stations.build_stations import build_stations
from weather.transform_weather import transform_weather
from data_io.s3_writer import write_outputs
from data_io.s3_reader import list_s3_jsonl_files
from load_to_mongo import init_indexes, migrate_data_stations, migrate_data_weather, check_integrity


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("prep_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():

    global_start = time.time()

    logger.info("Démarrage Pipeline")

    # Initialisation des index MongoDB
    init_indexes()

    # Construction du référentiel des stations
    stations = build_stations()
    logger.info("Référentiel des stations construit")

    all_clean = []
    all_rejects = []
    reports = []
    files_processed = 0

    for source_name, prefix in cfg.RAWS_PATH.items():

        source_start = time.time()
        logger.info(f"Traitement source : {source_name} | Prefixe S3 : {prefix}")

        # Liste des fichiers JSONL à traiter
        try:
            jsonl_files = list_s3_jsonl_files(prefix)
            logger.info(f"{len(jsonl_files)} fichiers JSONL trouvés pour la source {source_name}")
        except Exception as e:
            logger.error(f"Erreur lors de la liste des fichiers JSONL pour la source {source_name} avec le préfixe {prefix}", exc_info=True)
            reports.append({
                "source": source_name,
                "prefix": prefix,
                "total_rows": 0,
                "valid_rows": 0,
                "rejected_rows": 0,
                "error_rate": 1.0,
                "error": f"Erreur lors de la liste des fichiers JSONL: {str(e)}"
            })
            continue

        if not jsonl_files:
            logger.warning(f"Aucun fichier JSONL trouvé pour la source {source_name} avec le préfixe {prefix}")
            reports.append({
                "source": source_name,
                "prefix": prefix,
                "total_rows": 0,
                "valid_rows": 0,
                "rejected_rows": 0,
                "error_rate": 1.0,
                "error": "Aucun fichier JSONL trouvé"
            })
            continue

        for path in jsonl_files:
            file_start = time.time()
            logger.info(f"Traitement du fichier : {path}")
            try:
                clean_data, rejected_data, report = transform_weather(path, stations)
                files_processed += 1
            except Exception as e:
                logger.error(f"Problème lors du traitement du fichier {path}", exc_info=True)
                clean_data = pd.DataFrame()
                rejected_data = pd.DataFrame()
                report = {
                    "total_rows": 0,
                    "valid_rows": 0,
                    "rejected_rows": 0,
                    "error_rate": 1.0,
                    "error": f"Erreur lors du traitement du fichier: {str(e)}"
                }

            # On ajoute uniquement des DataFrame valides
            if clean_data is not None and not clean_data.empty:
                all_clean.append(clean_data)
            if rejected_data is not None and not rejected_data.empty:
                all_rejects.append(rejected_data)

            report["source"] = source_name
            report["file"] = path
            report["processing_time_seconds"] = round(time.time() - file_start, 2)
            reports.append(report)

        source_duration = round(time.time() - source_start, 2)
        logger.info(f"Fin du traitement de la source {source_name} | Durée : {source_duration} secondes")

    # Fusion finale
    weather_data = (pd.concat(all_clean, ignore_index=True) if all_clean else pd.DataFrame())
    rejects = (pd.concat(all_rejects, ignore_index=True) if all_rejects else pd.DataFrame())

    total_rows = sum(r.get("total_rows", 0) for r in reports)
    rejected_rows = sum(r.get("rejected_rows", 0) for r in reports)

    # Report global
    global_report = {
        "total_rows": total_rows,
        "valid_rows": sum(r.get("valid_rows", 0) for r in reports),
        "rejected_rows": rejected_rows,
        "files_processed": files_processed,
        "error_rate": (rejected_rows / total_rows if total_rows > 0 else 0.0),
        "total_processing_time_seconds": round(time.time() - global_start, 2)
    }

    logger.info(f"Pipeline terminé | "
                f"Total: {global_report['total_rows']} | "
                f"Valides: {global_report['valid_rows']} | "
                f"Rejetées: {global_report['rejected_rows']} | "
                f"Fichiers traités: {global_report['files_processed']} | "
                f"Taux d'erreur: {global_report['error_rate']:.2%} | "
                f"Temps de traitement total: {global_report['total_processing_time_seconds']} secondes"
    )

    # Ecrit les résultats du pipeline dans le bucket s3
    write_outputs(weather_data, rejects, global_report, cfg.BUCKET_NAME)

    # Migrer les données vers MongoDB
    try:
        migrate_data_stations(stations)
        migrate_data_weather(weather_data)
        check_integrity()
        logger.info("Migration vers MongoDB réussie et intégrité vérifiée")
    except Exception as e:
        logger.error("Erreur lors de la migration vers MongoDB ou de la vérification de l'intégrité", exc_info=True)


if __name__ == '__main__':
    main()