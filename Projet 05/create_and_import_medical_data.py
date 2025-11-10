import pandas as pd
from pymongo import MongoClient, errors
from datetime import datetime
import subprocess
import os
import time


# -----------------------------
# 🧪 TEST D’INTÉGRITÉ
# -----------------------------
print("🔍 Exécution du test d’intégrité des données...")
result = subprocess.run(["python", "test_integrity.py"], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("❌ Échec du test d’intégrité — import annulé.")
    exit(1)
print("✅ Test d’intégrité terminé — démarrage de la migration.\n")


# -----------------------------
# ⚙️ PARAMÈTRES
# -----------------------------
MONGO_URI = os.getenv("MONGO_URI", f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}@{os.getenv('MONGO_HOST', 'localhost')}:27017/?authSource={os.getenv('MONGO_INITDB_DATABASE', 'admin')}")
DB_NAME = "medical_data"
COLLECTION_NAME = "admissions"
CSV_FILE = "medical_data.csv"


# -----------------------------
# 🚀 CONNEXION À MONGODB
# -----------------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Si la collection existe déjà, on la supprime pour repartir proprement
if COLLECTION_NAME in db.list_collection_names():
    db[COLLECTION_NAME].drop()
    print(f"🧹 Collection '{COLLECTION_NAME}' supprimée.")

# Récupération de la collection créée via 02-create-collections.js
collection = db[COLLECTION_NAME]
print(f"✅ Collection '{COLLECTION_NAME}' prête (schéma déjà défini dans l’initialisation MongoDB).")

# -----------------------------
# 🧱 CRÉATION D’UN INDEX UNIQUE
# -----------------------------
collection.create_index(
    [
        ("patient.name", 1),
        ("patient.age", 1),
        ("patient.gender", 1),
        ("patient.blood_type", 1),
        ("admission.date", 1)
    ],
    unique=True,
    name="unique_patient"
)
print("🔒 Index unique créé sur (patient.name, admission.date)")

# -----------------------------
# 📂 LECTURE DU CSV
# -----------------------------
df = pd.read_csv(CSV_FILE, sep=None, engine="python")

# Nettoyage et normalisation des colonnes
df.columns = (
    df.columns.str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

# Conversion des dates et nombres
date_cols = ["date_of_admission", "discharge_date"]
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors="coerce")

df["billing_amount"] = pd.to_numeric(df["billing_amount"], errors="coerce")
df["age"] = pd.to_numeric(df["age"], errors="coerce")
df["room_number"] = pd.to_numeric(df["room_number"], errors="coerce")

# Remplace NaN par None
df = df.where(pd.notnull(df), None)

# -----------------------------
# 🧠 STRUCTURATION DES DOCUMENTS
# -----------------------------
documents = []
for _, row in df.iterrows():

    # Sécurise la conversion date_of_admission
    admission_date = (
        row["date_of_admission"].to_pydatetime()
        if pd.notna(row["date_of_admission"])
        else None
    )

    discharge_date = (
        row["discharge_date"].to_pydatetime()
        if pd.notna(row["discharge_date"])
        else None
    )

    doc = {
        "patient": {
            "name": row["name"],
            "age": int(row["age"]) if row["age"] is not None else None,
            "gender": row["gender"],
            "blood_type": row["blood_type"],
            "insurance_provider": row["insurance_provider"],
        },
        "admission": {
            "date": admission_date,
            "type": row["admission_type"],
            "room_number": int(row["room_number"]) if row["room_number"] is not None else None,
            "billing_amount": float(row["billing_amount"]) if row["billing_amount"] is not None else None,
            "discharge_date": discharge_date,
            "doctor": row["doctor"],
            "hospital": row["hospital"],
        },
        "medical": {
            "condition": row["medical_condition"],
            "medication": row["medication"],
            "test_results": row["test_results"],
        },
    }
    documents.append(doc)

# -----------------------------
# 📥 INSERTION AVEC VÉRIFICATION DES DOUBLONS
# -----------------------------
inserted_count = 0
duplicate_count = 0

for doc in documents:
    try:
        collection.insert_one(doc)
        inserted_count += 1
    except errors.DuplicateKeyError:
        duplicate_count += 1

print(f"✅ {inserted_count} documents insérés avec succès.")
print(f"⚠️ {duplicate_count} doublons détectés et ignorés.")

# -----------------------------
# 📊 CONTRÔLE FINAL
# -----------------------------
print(f"📈 Nombre total de documents dans la collection : {collection.count_documents({})}")
print("🎉 Import terminé avec vérification des doublons !")
