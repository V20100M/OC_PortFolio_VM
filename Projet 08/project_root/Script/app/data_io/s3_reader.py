import boto3
import logging
import pandas as pd

from typing import List
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


def read_json_from_s3(path: str) -> pd.DataFrame:
    # Lit un fichier JSONL depuis S3 et retourne un DataFrame pandas
	return pd.read_json(path, lines=True)



def list_s3_jsonl_files(s3_prefix: str) -> List[str]:
    # Liste les fichiers .jsonl dans un préfixe S3 donné, triés par date de modification
    if not s3_prefix.startswith("s3://"):
        raise ValueError(
            f"Le préfixe doit commencer par 's3://', mais a reçu: {s3_prefix}"
        )

    parsed = urlparse(s3_prefix)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")

    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    jsonl_objects = []

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]

                # Ignore "dossiers"
                if key.endswith("/"):
                    continue

                if key.lower().endswith(".jsonl"):
                    jsonl_objects.append(
                        {"key": key, "last_modified": obj["LastModified"]}
                    )

    except Exception:
        logger.error(f"Erreur lors du listing S3 pour {s3_prefix}", exc_info=True)
        raise

    if not jsonl_objects:
        logger.warning(f"Aucun fichier .jsonl trouvé dans le préfixe {s3_prefix}")
        return []

    # Tri par date réelle
    jsonl_objects.sort(key=lambda x: x["last_modified"])

    jsonl_files = [f"s3://{bucket}/{obj['key']}" for obj in jsonl_objects]

    logger.info(
        f"{len(jsonl_files)} fichier(s) .jsonl trouvé(s) dans le préfixe {s3_prefix}"
    )

    return jsonl_files



#def read_excel_from_s3(path):
#	df_dict = pd.read_excel(path, sheet_name=None)
#	return df_dict