import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Clés API
MISTRAL_API_KEY  = os.getenv('MISTRAL_API_KEY')
OPEN_AGENDA_KEY = os.getenv("OPEN_AGENDA_KEY")

# URLs
OPEN_AGENDA_URL = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records"

# Modèles
EMBEDDING_MODEL = "mistral-embed"
LLM_MODEL = "mistral-small-latest"

# Filtres géographiques et temporels
GEO_FILTER_FIELD = "location_department"    # utiliser "location_city" pour filtrer par ville, "location_region" pour filtrer par région
GEO_FILTER_VALUE = "Gironde"                # utiliser le nom de la ville ou de la région correspondante si vous changez le champ de filtrage
DATE_NOW = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
DATE_MAX = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")

# Champs utiles à conserver dans le DataFrame final
CHAMPS_UTILES = [
    "uid", "title_fr", "description_fr", "longdescription_fr",
    "firstdate_begin", "lastdate_end", "location_name",
    "location_city", "location_department", "location_region",
    "location_address", "conditions_fr", "keywords_fr"
]

# Paramètres de récupération des événements
BATCH_SIZE = 100  # Maximum de résultats à récupérer par requête (limite de l'API)
MAX_EVENTS = 5000 # Limite de sécurité pour le POC

# Paramètres de découpage du texte
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Paramètres de recherche dans Faiss
TOP_K = 10   # Nombre de chunks récupérés depuis Faiss

# Chemins des fichiers
EVENTS_CSV = "data/events.csv"
EVENTS_JSON = "data/events.json"
SANS_VILLE = "data/events_sans_ville.csv"
EMBEDDINGS_NPY = "data/embeddings.npy"
FAISS_INDEX = "data/faiss_index.bin"
FAISS_METADATAS = "data/faiss_metadatas.json"
TEST_DATASET_JSON = "data/test_dataset.json"
EVALUATION_REPORT_JSON = "data/evaluation_report.json"