import os
import logging
import pandas as pd
import boto3
import time
import requests
import config as cfg
from datetime import datetime, time as dtime

# Dossier de sortie pour les fichiers préparés
OUTPUT_DIR = r"C:\Users\20100\Desktop\Data Engineer\Projet 08\project_root\Script\prepared_excel"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("prep_airbyte.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")

# Téléchargement du fichier depuis l'URL
def download_file(url: str, destination: str):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(destination, "wb") as f:
            f.write(response.content)
        logger.info(f"Fichier téléchargé depuis {url} vers {destination}")
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement de {url} : {e}", exc_info=True)

# Upload vers S3
def upload_file_to_s3(local_path: str, filename: str, subfolder: str):
    s3_key = f"{cfg.S3_PREFIX}{subfolder}/{filename}"
    try:
        s3_client.upload_file(local_path, cfg.BUCKET_NAME, s3_key)
        logger.info(f"Fichier {local_path} uploadé vers s3://{cfg.BUCKET_NAME}/{s3_key}")
    except Exception as e:
        logger.error(f"Erreur lors de l'upload de {local_path} vers s3://{cfg.BUCKET_NAME}/{s3_key} : {e}", exc_info=True)


def _find_time_column(df: pd.DataFrame) -> str | None:
    # Normalise les noms de colonnes pour retrouver Time même si espaces / casse
    cols_norm = {c.strip().lower(): c for c in df.columns}
    return cols_norm.get("time")


def _time_series_to_string(s: pd.Series) -> pd.Series:
    # Normalise une série contenant des heures en string au format "HH:MM:SS", en gérant les cas datetime, time, string, etc.
    s = s.copy()

    # Cas datetime64
    if pd.api.types.is_datetime64_any_dtype(s):
        return s.dt.strftime("%H:%M:%S")

    # Cas objets python time
    first_valid = s.dropna().iloc[0] if not s.dropna().empty else None
    if isinstance(first_valid, dtime):
        return s.apply(lambda x: x.strftime("%H:%M:%S") if isinstance(x, dtime) else str(x))

    # Cas string / numeric
    return s.astype(str).str.strip()


#def merge_excel_sheets_with_datetime(source_dir: str, output_dir: str) -> None:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(source_dir):
        if not filename.endswith(".xlsx"):
            continue

        filepath = os.path.join(source_dir, filename)
        logger.info(f"Traitement fichier : {filename}")

        try:
            xls = pd.ExcelFile(filepath)
        except Exception as e:
            logger.error(f"Impossible de lire {filename} : {e}")
            continue

        dfs = []

        for sheet_name in xls.sheet_names:
            # Feuille = date au format ddmmyy
            try:
                sheet_date = datetime.strptime(sheet_name, "%d%m%y")
            except ValueError:
                logger.warning(f"Feuille ignorée (format invalide) : {sheet_name}")
                continue

            df = pd.read_excel(filepath, sheet_name=sheet_name)

            # Supprime lignes totalement vides (dont la 2e ligne vide)
            df = df.dropna(how="all")

            # Nettoie les noms de colonnes
            df.columns = [c.strip() for c in df.columns]

            time_col = _find_time_column(df)
            if not time_col:
                logger.warning(f"Colonne 'Time' absente dans {filename} / {sheet_name}")
                continue

            # Supprime les lignes où Time est vide
            df = df[df[time_col].notna()].copy()
            if df.empty:
                logger.warning(f"Aucune donnée exploitable dans {filename} / {sheet_name}")
                continue

            # Convertit Time en string robuste
            time_str = _time_series_to_string(df[time_col])

            # Construit la string datetime
            base_date_str = sheet_date.strftime("%Y-%m-%d")
            datetime_str = base_date_str + " " + time_str

            # Tentative 1 : format "12:04 AM"
            dh = pd.to_datetime(datetime_str, format="%Y-%m-%d %I:%M %p", errors="coerce")
            # Tentative 2 : format "00:04:00"
            dh2 = pd.to_datetime(datetime_str, format="%Y-%m-%d %H:%M:%S", errors="coerce")

            df["dh_utc"] = dh.fillna(dh2)

            # Garde uniquement les lignes valides
            before = len(df)
            df = df[df["dh_utc"].notna()].copy()
            after = len(df)

            if after == 0:
                logger.error(f"0 ligne valide après parsing dh_utc dans {filename} / {sheet_name}")
                continue

            logger.info(f"{filename} / {sheet_name} : {after}/{before} lignes valides")

            #df["dh_utc"] = df["dh_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")

            # Option : on retire Time (puisqu’on a dh_utc)
            df.drop(columns=[time_col], inplace=True)

            dfs.append(df)

        if not dfs:
            logger.warning(f"Aucune feuille valide pour {filename}")
            continue

        merged_df = pd.concat(dfs, ignore_index=True)

        output_path = os.path.join(output_dir, filename)
        merged_df.to_excel(output_path, index=False)
        logger.info(f"Fichier généré : {output_path}")

        # Upload vers S3
        upload_file_to_s3(output_path, filename)



def process_excel_files(local_path: str, filename: str, subfolder: str):
    file_start = time.time()
    logger.info(f"Début du traitement de {filename}")

    try:
        with pd.ExcelFile(local_path) as xls:
                dfs = []

                for sheet_name in xls.sheet_names:
                    # Feuille = date au format ddmmyy
                    try:
                        sheet_date = datetime.strptime(sheet_name, "%d%m%y")
                    except ValueError:
                        logger.warning(f"Feuille ignorée (format invalide) : {sheet_name}")
                        continue

                    df = pd.read_excel(local_path, sheet_name=sheet_name)

                    # Supprime lignes totalement vides (dont la 2e ligne vide)
                    df = df.dropna(how="all")

                    # Nettoie les noms de colonnes
                    df.columns = [c.strip() for c in df.columns]

                    time_col = _find_time_column(df)
                    if not time_col:
                        logger.warning(f"Colonne 'Time' absente dans {filename} / {sheet_name}")
                        continue

                    # Supprime les lignes où Time est vide
                    df = df[df[time_col].notna()].copy()
                    if df.empty:
                        logger.warning(f"Aucune donnée exploitable dans {filename} / {sheet_name}")
                        continue

                    # Convertit Time en string robuste
                    time_str = _time_series_to_string(df[time_col])

                    # Construit la string datetime
                    base_date_str = sheet_date.strftime("%Y-%m-%d")
                    datetime_str = base_date_str + " " + time_str

                    # Tentative 1 : format "12:04 AM"
                    dh = pd.to_datetime(datetime_str, format="%Y-%m-%d %I:%M %p", errors="coerce")
                    # Tentative 2 : format "00:04:00"
                    dh2 = pd.to_datetime(datetime_str, format="%Y-%m-%d %H:%M:%S", errors="coerce")

                    df["dh_utc"] = dh.fillna(dh2)

                    # Garde uniquement les lignes valides
                    before = len(df)
                    df = df[df["dh_utc"].notna()].copy()
                    after = len(df)

                    if after == 0:
                        logger.error(f"0 ligne valide après parsing dh_utc dans {filename} / {sheet_name}")
                        continue

                    logger.info(f"{filename} / {sheet_name} : {after}/{before} lignes valides")

                    # Option : on retire Time (puisqu’on a dh_utc)
                    df.drop(columns=[time_col], inplace=True)

                    dfs.append(df)

    except Exception as e:
        logger.error(f"Impossible de lire {filename} : {e}", exc_info=True)
        return

    if not dfs:
        logger.warning(f"Aucune feuille valide pour {filename}")
        return

    merged_df = pd.concat(dfs, ignore_index=True)

    output_path = os.path.join(OUTPUT_DIR, filename)
    merged_df.to_excel(output_path, index=False)
    logger.info(f"Fichier généré : {output_path}")

    # Upload vers S3
    upload_file_to_s3(output_path, filename, subfolder)

    duration = round(time.time() - file_start, 2)
    logger.info(f"Fin du traitement de {filename} (durée : {duration:.2f} secondes)")



def main():
    global_start = time.time()
    logger.info("=== Démarrage du processus de préparation des fichiers Airbyte ===")

    for key, file_info in cfg.PUBLIC_EXCEL_FILES.items():

        filename = file_info["filename"]
        url = file_info["url"]
        subfolder = file_info["s3_subfolder"]

        download_start = time.time()
        logger.info(f"Début du téléchargement de {filename} depuis {url}")

        local_temp_path = os.path.join(OUTPUT_DIR, f"temp_{filename}")

        try:
            download_file(url, local_temp_path)
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de {filename} : {e}", exc_info=True)
            continue

        download_duration = round(time.time() - download_start, 2)
        logger.info(f"Fin du téléchargement de {filename} (durée : {download_duration:.2f} secondes)")

        process_excel_files(local_temp_path, filename, subfolder)

        try:
            os.remove(local_temp_path)
            logger.info(f"Fichier temporaire supprimé : {local_temp_path}")
        except Exception as e:
            logger.warning(f"Impossible de supprimer le fichier temporaire {local_temp_path} : {e}")

    total_duration = round(time.time() - global_start, 2)
    logger.info(f"=== Fin du processus de préparation des fichiers Airbyte (durée totale : {total_duration:.2f} secondes) ===")



if __name__ == "__main__":
    main()