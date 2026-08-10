import requests
import pandas as pd
from config import OPEN_AGENDA_KEY, OPEN_AGENDA_URL, GEO_FILTER_FIELD, GEO_FILTER_VALUE, CHAMPS_UTILES, BATCH_SIZE, MAX_EVENTS, DATE_MAX, DATE_NOW, get_geo_paths
import os

# Récupération des données
def fetch_events(geo_field=None, geo_value=None):
    geo_field = geo_field or GEO_FILTER_FIELD
    geo_value = geo_value or GEO_FILTER_VALUE

    all_events = []
    offset = 0

    where_clause = f"{geo_field}='{geo_value}' AND lastdate_end >= '{DATE_NOW}' AND lastdate_end <= '{DATE_MAX}'"

    print(f"Filtre : {where_clause}")
    print("Récupération en cours...")

    while True:
        params = {
            "limit": BATCH_SIZE,
            "offset": offset,
            "api_key": OPEN_AGENDA_KEY,
            "where": where_clause,
        }

        response = requests.get(OPEN_AGENDA_URL, params=params)

        if response.status_code != 200:
            print(f"Erreur API : {response.status_code} - {response.json()}")
            break

        data = response.json()
        results = data.get("results", [])
        total = data.get("total_count", 0)

        if offset == 0:
            print(f"Total d'événements trouvés : {total}")

        if not results:
            break

        all_events.extend(results)
        offset += BATCH_SIZE

        print(f"  Récupérés : {len(all_events)} / {min(total, MAX_EVENTS)}", end="\r")

        if len(all_events) >= MAX_EVENTS or len(all_events) >= total:
            print("\nLimite de récupération atteinte.")
            break

    print(f"Récupération terminée. Total d'événements récupérés : {len(all_events)}")
    return all_events


# Nettoyage des données
def clean_events(events, geo_field=None, paths=None):
    geo_field = geo_field or GEO_FILTER_FIELD
    paths = paths or get_geo_paths(GEO_FILTER_FIELD, GEO_FILTER_VALUE)

    # Création du dossier de destination dès le départ, quel que soit le cas
    # rencontré ensuite (évite tout risque d'écriture avant création du dossier)
    os.makedirs(paths["base_dir"], exist_ok=True)

    df = pd.DataFrame(events)

    # Garder uniquement les champs pertinents dans le dataframe
    cols_disponibles = [c for c in CHAMPS_UTILES if c in df.columns]
    df = df[cols_disponibles]

    print(f"\n--- Avant nettoyage ---")
    print(f"Lignes : {len(df)}")
    print(f"Valeurs manquantes par colonne :\n{df.isnull().sum()}")

    # Supprimer les événements sans titre
    df = df.dropna(subset=["title_fr"])

    # Supprimer les événements sans description (inutilisables pour la vectorisation)
    df = df.dropna(subset=["description_fr"])

    # Remplir les champs textes manquants par une chaîne vide (pour éviter les erreurs lors de la vectorisation)
    text_cols = ["longdescription_fr", "conditions_fr", "keywords_fr"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("")

    # Supprimer les doublons sur uid
    df = df.drop_duplicates(subset=["uid"])

    # Convertir les dates en format datetime
    for date_col in ["firstdate_begin", "lastdate_end"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)

    # Filtrer les événements de plus d'un an
    date_now_dt = pd.Timestamp(DATE_NOW).tz_localize("UTC")
    date_max_dt = pd.Timestamp(DATE_MAX).tz_localize("UTC")
    avant = len(df)
    df = df[(df["lastdate_end"] >= date_now_dt) & (df["lastdate_end"] <= date_max_dt)]
    apres = len(df)
    if avant - apres > 0:
        print(f"Filtrage temporel : {avant - apres} événements supprimés (datant de plus d'un an)")

    # Vérifier que geo_field existe dans le dataframe
    if geo_field not in df.columns:
        raise ValueError(f"Le champ de filtrage géographique '{geo_field}' est absent du DataFrame. "
                         f"Vérifiez la valeur de geo_field/GEO_FILTER_FIELD.")

    # Ecarter les événements sans ville et les sauvegarder dans un fichier à part pour analyse
    sans_ville = df[df["location_city"].isnull() | (df["location_city"].str.strip() == "")]
    if len(sans_ville) > 0:
        sans_ville.to_csv(paths["sans_ville"], index=False, encoding="utf-8-sig")
        print(f"\n{len(sans_ville)} événements sans ville trouvés. Sauvegarde dans '{paths['sans_ville']}' pour analyse.")
        df = df[df["location_city"].notnull() & (df["location_city"].str.strip() != "")]

    print(f"\n--- Après nettoyage ---")
    print(f"Lignes : {len(df)}")
    print(f"Colonnes : {list(df.columns)}")

    return df

# Sauvegarde
def save_events(df, paths=None):
    paths = paths or get_geo_paths(GEO_FILTER_FIELD, GEO_FILTER_VALUE)
    os.makedirs(paths["base_dir"], exist_ok=True)
    df.to_csv(paths["events_csv"], index=False, encoding="utf-8-sig")
    df.to_json(paths["events_json"], orient="records", force_ascii=False, indent=2, date_format="iso")
    print(f"\nFichiers sauvegardés : {paths['events_csv']} et {paths['events_json']}")

# Main
if __name__ == "__main__":
    default_paths = get_geo_paths(GEO_FILTER_FIELD, GEO_FILTER_VALUE)
    events_bruts = fetch_events()
    df_clean = clean_events(events_bruts, paths=default_paths)
    save_events(df_clean, paths=default_paths)
    print(f"\nJeu de données final : {len(df_clean)} événements prêts à être indexés")