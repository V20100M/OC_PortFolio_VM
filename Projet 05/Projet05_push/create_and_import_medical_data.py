import pandas as pd
from pymongo import MongoClient, errors
from datetime import datetime
import subprocess
import os
import time


# 🧪 test d’intégrité
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
CSV_FILE = "medical_data.csv"  # <-- Mets ici le chemin vers ton fichier CSV


# -----------------------------
# 🚀 CONNEXION À MONGODB
# -----------------------------
max_retries = 10
for attempt in range(max_retries):
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ Connexion MongoDB réussie.")
        break
    except Exception as e:
        print(f"⏳ Tentative {attempt+1}/{max_retries} : MongoDB pas encore prêt ({e})")
        time.sleep(5)
else:
    print("❌ MongoDB inaccessible après plusieurs tentatives. Arrêt du script.")
    exit(1)

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Si la collection existe déjà, on la supprime pour repartir proprement
if COLLECTION_NAME in db.list_collection_names():
    db[COLLECTION_NAME].drop()
    print(f"🧹 Collection '{COLLECTION_NAME}' supprimée.")

# -----------------------------
# 🧱 CRÉATION DE LA COLLECTION AVEC VALIDATION JSON SCHEMA
# -----------------------------
schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["patient", "admission", "medical"],
        "properties": {
            "patient": {
                "bsonType": "object",
                "required": ["name", "age", "gender", "blood_type", "insurance_provider"],
                "properties": {
                    "name": {"bsonType": "string"},
                    "age": {"bsonType": "int"},
                    "gender": {"enum": ["Male", "Female"]},
                    "blood_type": {
                        "enum": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
                    },
                    "insurance_provider": {
                        "enum": ["Aetna", "Blue Cross", "Cigna", "Medicare", "UnitedHealthcare"]
                    },
                },
            },
            "admission": {
                "bsonType": "object",
                "required": ["date", "type"],
                "properties": {
                    "date": {"bsonType": "date"},
                    "type": {"enum": ["Elective", "Emergency", "Urgent"]},
                    "room_number": {"bsonType": ["int", "null"]},
                    "billing_amount": {"bsonType": ["double", "null"]},
                    "discharge_date": {"bsonType": ["date", "null"]},
                    "doctor": {"bsonType": "string"},
                    "hospital": {"bsonType": "string"},
                },
            },
            "medical": {
                "bsonType": "object",
                "required": ["condition", "medication", "test_results"],
                "properties": {
                    "condition": {
                        "enum": [
                            "Arthritis",
                            "Asthma",
                            "Cancer",
                            "Diabetes",
                            "Hypertension",
                            "Obesity",
                        ]
                    },
                    "medication": {
                        "enum": [
                            "Aspirin",
                            "Ibuprofen",
                            "Lipitor",
                            "Paracetamol",
                            "Penicillin",
                        ]
                    },
                    "test_results": {
                        "enum": ["Abnormal", "Inconclusive", "Normal"]
                    },
                },
            },
        },
    }
}

db.create_collection(COLLECTION_NAME, validator=schema)
collection = db[COLLECTION_NAME]
print(f"✅ Collection '{COLLECTION_NAME}' créée avec schéma de validation.")

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
df = pd.read_csv(CSV_FILE)

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
    doc = {
        "patient": {
            "name": row["name"],
            "age": int(row["age"]) if row["age"] is not None else None,
            "gender": row["gender"],
            "blood_type": row["blood_type"],
            "insurance_provider": row["insurance_provider"],
        },
        "admission": {
            "date": row["date_of_admission"].to_pydatetime() if row["date_of_admission"] else None,
            "type": row["admission_type"],
            "room_number": int(row["room_number"]) if row["room_number"] else None,
            "billing_amount": float(row["billing_amount"]) if row["billing_amount"] else None,
            "discharge_date": row["discharge_date"].to_pydatetime() if row["discharge_date"] else None,
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
