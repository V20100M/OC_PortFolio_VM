import os
import re
import unicodedata
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Répertoire racine des données générées par localisation
DATA_DIR = "data"

# Clés API
MISTRAL_API_KEY  = os.getenv('MISTRAL_API_KEY')
OPEN_AGENDA_KEY = os.getenv("OPEN_AGENDA_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = "evenements"

PIPELINE_DIR = os.path.join(DATA_DIR, "pipeline")
PIPELINE_RAW_JSON = os.path.join(PIPELINE_DIR, "bronze_input.json")
PIPELINE_GOLD_JSON = os.path.join(PIPELINE_DIR, "gold_input.json")

# URLs
OPEN_AGENDA_URL = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records"

# Modèles
EMBEDDING_MODEL = "mistral-embed"
LLM_MODEL = "mistral-small-latest"
SMOLAGENTS_MODEL = "mistral/mistral-small-latest"

# Filtres géographiques et temporels
# Valeurs par défaut, utilisées si l'app est lancée en CLI (scripts/) sans
# passer par l'écran de géolocalisation de app.py
GEO_FILTER_FIELD = "location_department"    # "location_city" | "location_department" | "location_region"
GEO_FILTER_VALUE = "Gironde"
DATE_NOW = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
DATE_MAX = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")

# Correspondance niveau de recherche <-> champ Open Agenda
# Utilisé dans app.py pour le choix du rayon de recherche (Ville/Département/Région)
GEO_LEVELS = {
    "Ville": "location_city",
    "Département": "location_department",
    "Région": "location_region",
}

# Champs utiles à conserver dans le DataFrame final
CHAMPS_UTILES = [
    "uid", "title_fr", "description_fr", "longdescription_fr",
    "firstdate_begin", "lastdate_end", "location_name",
    "location_city", "location_department", "location_region",
    "location_address", "conditions_fr", "keywords_fr"
]

# Paramètres de récupération des événements
BATCH_SIZE = 100  # Maximum de résultats à récupérer par requête (limite de l'API)
MAX_EVENTS = 100000 # Limite pour le MVP

# Paramètres de découpage du texte
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 150

# Paramètres de recherche dans Faiss
TOP_K = 10   # Nombre de chunks récupérés depuis Faiss

# Chemins des fichiers (rétrocompatibilité CLI / scripts lancés sans géoloc dynamique)
EVENTS_CSV = "data/events.csv"
EVENTS_JSON = "data/events.json"
SANS_VILLE = "data/events_sans_ville.csv"
EMBEDDINGS_NPY = "data/embeddings.npy"
FAISS_INDEX = "data/faiss_index.bin"
FAISS_METADATAS = "data/faiss_metadatas.json"
TEST_DATASET_JSON = "data/test_dataset.json"
EVALUATION_REPORT_JSON = "data/evaluation_report.json"
FEEDBACK_JSON = "data/feedback.json"


def slugify(value):
    """Transforme une valeur ('Nouvelle-Aquitaine', 'Saint-Étienne'...) en
    identifiant de dossier sûr ('nouvelle_aquitaine', 'saint_etienne')."""
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w]+", "_", value.strip().lower())
    return value.strip("_")


def get_geo_paths(geo_field, geo_value):
    """
    Construit les chemins de fichiers (events, embeddings, index Faiss...)
    dédiés à une combinaison (geo_field, geo_value) donnée, ex :
    ("location_department", "Gironde") -> data/location_department_gironde/...
    Permet de mettre en cache les données déjà collectées/vectorisées par
    localisation, sans tout régénérer à chaque utilisateur.
    """
    slug = f"{geo_field}_{slugify(geo_value)}"
    base = os.path.join(DATA_DIR, slug)
    return {
        "base_dir": base,
        "events_csv": os.path.join(base, "events.csv"),
        "events_json": os.path.join(base, "events.json"),
        "sans_ville": os.path.join(base, "events_sans_ville.csv"),
        "embeddings_npy": os.path.join(base, "embeddings.npy"),
        "faiss_index": os.path.join(base, "faiss_index.bin"),
        "faiss_metadatas": os.path.join(base, "faiss_metadatas.json"),
    }