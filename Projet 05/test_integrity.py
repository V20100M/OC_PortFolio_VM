"""
test_integrity.py
----------------------------------------
Test d’intégrité du dataset médical avant migration vers MongoDB.

Vérifie :
  ✅ colonnes attendues
  ✅ typage des données
  ✅ valeurs manquantes
  ✅ doublons (basés sur Name + Age + Gender + Blood Type + Date of Admission)
  ✅ estimation des doublons “à ignorer” (comme dans l’import MongoDB)
"""

import pandas as pd
from datetime import datetime

# -----------------------------
# ⚙️ PARAMÈTRES
# -----------------------------
CSV_FILE = "medical_data.csv"

EXPECTED_COLUMNS = [
    "Name",
    "Age",
    "Gender",
    "Blood Type",
    "Date of Admission",
    "Admission Type",
    "Room Number",
    "Billing Amount",
    "Discharge Date",
    "Medical Condition",
    "Medication",
    "Test Results",
    "Doctor",
    "Hospital",
    "Insurance Provider",
]

duplicate_subset = [
    "Name",
    "Age",
    "Gender",
    "Blood Type",
    "Date of Admission",
]

# -----------------------------
# 📂 LECTURE DU CSV
# -----------------------------
try:
    df = pd.read_csv(CSV_FILE, sep=None, engine="python")
    print(f"✅ Fichier '{CSV_FILE}' chargé avec succès.")
except FileNotFoundError:
    print(f"❌ ERREUR : le fichier '{CSV_FILE}' est introuvable.")
    exit(1)
except Exception as e:
    print(f"❌ ERREUR lors du chargement du fichier : {e}")
    exit(1)

# -----------------------------
# 🧩 VÉRIFICATION DES COLONNES
# -----------------------------
missing_cols = [col for col in EXPECTED_COLUMNS if col not in df.columns]
extra_cols = [col for col in df.columns if col not in EXPECTED_COLUMNS]

if missing_cols:
    print(f"⚠️ Colonnes manquantes : {missing_cols}")
else:
    print("✅ Toutes les colonnes attendues sont présentes.")

if extra_cols:
    print(f"ℹ️ Colonnes supplémentaires détectées : {extra_cols}")

# -----------------------------
# 🔢 CONTRÔLE DES TYPES
# -----------------------------
type_errors = []

if not pd.api.types.is_numeric_dtype(df["Age"]):
    type_errors.append("Age non numérique")

if not pd.api.types.is_numeric_dtype(df["Billing Amount"]):
    type_errors.append("Billing Amount non numérique")

if type_errors:
    print(f"⚠️ Erreurs de typage détectées : {type_errors}")
else:
    print("✅ Les types de colonnes principales sont corrects.")

# -----------------------------
# 🗓️ CONTRÔLE AVANCÉ DES DATES
# -----------------------------
date_errors = []

# Conversion sécurisée
df["Date of Admission"] = pd.to_datetime(df["Date of Admission"], errors="coerce", dayfirst=True)
df["Discharge Date"] = pd.to_datetime(df["Discharge Date"], errors="coerce", dayfirst=True)

# 1️⃣ Dates invalides (NaT)
invalid_admission = df[df["Date of Admission"].isna()]
invalid_discharge = df[df["Discharge Date"].isna()]

if len(invalid_admission) > 0:
    print(f"⚠️ {len(invalid_admission)} dates d’admission invalides (NaT ou format incorrect)")
    print(invalid_admission[["Name", "Date of Admission"]].head())

if len(invalid_discharge) > 0:
    print(f"⚠️ {len(invalid_discharge)} dates de sortie invalides (NaT ou format incorrect)")
    print(invalid_discharge[["Name", "Discharge Date"]].head())

# 2️⃣ Dates dans le futur (incohérence)
future_dates = df[df["Date of Admission"] > pd.Timestamp.now()]

if len(future_dates) > 0:
    print(f"⚠️ {len(future_dates)} dates d’admission dans le futur détectées")
    print(future_dates[["Name", "Date of Admission"]].head())

# 3️⃣ Discharge Date < Admission Date
invalid_chronology = df[
    (df["Date of Admission"].notna()) &
    (df["Discharge Date"].notna()) &
    (df["Discharge Date"] < df["Date of Admission"])
]

if len(invalid_chronology) > 0:
    print(f"⚠️ {len(invalid_chronology)} incohérences chronologiques détectées (sortie avant admission)")
    print(invalid_chronology[["Name", "Date of Admission", "Discharge Date"]].head())

# Si au moins une erreur a été détectée
if len(invalid_admission) > 0 or len(invalid_discharge) > 0 or len(future_dates) > 0 or len(invalid_chronology) > 0:
    print("⚠️ Erreurs de dates détectées")
else:
    print("✅ Toutes les dates sont valides")

# -----------------------------
# 🚨 VALEURS MANQUANTES
# -----------------------------
missing_values = df.isnull().sum()
missing_summary = missing_values[missing_values > 0]

if not missing_summary.empty:
    print("\n⚠️ Valeurs manquantes détectées :")
    print(missing_summary)
else:
    print("✅ Aucune valeur manquante détectée.")

# -----------------------------
# 🔁 DÉTECTION DES DOUBLONS
# -----------------------------
if set(duplicate_subset).issubset(df.columns):
    duplicates = df.duplicated(subset=duplicate_subset, keep=False)
    dup_total = duplicates.sum()  # Nombre total de lignes faisant partie d’un doublon

    unique_rows = df.drop_duplicates(subset=duplicate_subset, keep="first")
    dup_ignored = len(df) - len(unique_rows)  # Nombre de doublons à ignorer (comme MongoDB)

    if dup_total > 0:
        print(f"⚠️ {dup_total} doublons détectés (basés sur {duplicate_subset}).")
        print(f"⚠️ {dup_ignored} doublons seraient ignorés lors de l’import MongoDB.")
        print(f"✅ {len(unique_rows)} documents uniques utilisables pour l’insertion.")
        print(df.loc[duplicates, duplicate_subset].head())
    else:
        print("✅ Aucun doublon détecté.")
else:
    print("ℹ️ Impossible de vérifier les doublons : colonnes manquantes.")

# -----------------------------
# 📊 SYNTHÈSE GLOBALE
# -----------------------------
print("\n📋 SYNTHÈSE DU TEST D’INTÉGRITÉ")
print("----------------------------------------")
print(f"Nombre total de lignes : {len(df)}")
print(f"Colonnes présentes      : {len(df.columns)}")
print("----------------------------------------")
print("🏁 Test d’intégrité terminé.")
