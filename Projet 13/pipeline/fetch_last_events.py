"""
pipeline/fetch_last_events.py
-------------------------------
Recupere les evenements modifies depuis le dernier import connu (MAX
de updated_at_source en Bronze). Si la table est vide (premier lancement),
recupere l'ensemble des evenements francais des 2 prochaines annees, en
decoupant recursivement toute fenetre trop volumineuse (dichotomie) pour
rester sous le plafond de pagination d'Opendatasoft (offset+limit <= 10000).
"""

import json
import os
from datetime import datetime, timedelta
import requests
from backend.database import get_connection
from config import OPEN_AGENDA_KEY, OPEN_AGENDA_URL, PIPELINE_RAW_JSON, BATCH_SIZE, MAX_EVENTS

NB_JOURS_INITIAL = 730
SEUIL_SUR = 9000          # en dessous du plafond de 10000, marge de securite
TAILLE_MIN_FENETRE_H = 6  # ne descend pas en dessous de 6h de fenetre (garde-fou anti-boucle infinie)


def get_last_import_timestamp():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(updated_at_source) FROM evenements_bronze")
            return cur.fetchone()[0]
    finally:
        conn.close()


def build_where(debut, fin, updated_since=None):
    clauses = [f"location_countrycode='FR'"]
    if updated_since:
        clauses.append(f"updatedat >= '{updated_since.isoformat()}'")
    else:
        clauses.append(f"lastdate_end >= '{debut.strftime('%Y-%m-%dT%H:%M:%S')}'")
        clauses.append(f"lastdate_end <= '{fin.strftime('%Y-%m-%dT%H:%M:%S')}'")
    return " AND ".join(clauses)


def get_total_count(where_clause):
    params = {"limit": 1, "offset": 0, "api_key": OPEN_AGENDA_KEY, "where": where_clause}
    response = requests.get(OPEN_AGENDA_URL, params=params)
    response.raise_for_status()
    return response.json().get("total_count", 0)


def fetch_all_pages(where_clause):
    events = []
    offset = 0
    while True:
        params = {"limit": BATCH_SIZE, "offset": offset, "api_key": OPEN_AGENDA_KEY, "where": where_clause}
        response = requests.get(OPEN_AGENDA_URL, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
        events.extend(results)
        offset += BATCH_SIZE
        if offset >= data.get("total_count", 0):
            break
    return events


def fetch_range_recursif(debut, fin, profondeur=0):
    """Recupere une fenetre [debut, fin], en la decoupant en deux si elle
    depasse le seuil sur, recursivement jusqu'a rentrer sous le plafond."""
    where_clause = build_where(debut, fin)
    total = get_total_count(where_clause)
    indent = "  " * (profondeur + 1)

    if total <= SEUIL_SUR:
        print(f"{indent}{debut.strftime('%Y-%m-%d')} -> {fin.strftime('%Y-%m-%d')} : {total} evenements")
        return fetch_all_pages(where_clause)

    duree = fin - debut
    if duree.total_seconds() / 3600 <= TAILLE_MIN_FENETRE_H:
        print(f"{indent}ATTENTION : {debut.strftime('%Y-%m-%d %Hh')} -> {fin.strftime('%Y-%m-%d %Hh')} "
              f"contient {total} evenements sur une fenetre minimale, recuperation partielle.")
        return fetch_all_pages(where_clause)  # au-dela d'un certain point, on accepte la perte plutot que boucler indefiniment

    milieu = debut + duree / 2
    print(f"{indent}{debut.strftime('%Y-%m-%d')} -> {fin.strftime('%Y-%m-%d')} : {total} evenements "
          f"(> seuil, decoupage en 2)")
    events_gauche = fetch_range_recursif(debut, milieu, profondeur + 1)
    events_droite = fetch_range_recursif(milieu, fin, profondeur + 1)
    return events_gauche + events_droite


def fetch_events(since=None):
    if since:
        where_clause = build_where(None, None, updated_since=since)
        total = get_total_count(where_clause)
        print(f"Import incremental depuis : {since.isoformat()} ({total} evenements)")
        events = fetch_all_pages(where_clause)
        print(f"{len(events)} evenements recuperes.")
        return events[:MAX_EVENTS]

    print(f"Aucun import precedent : import initial (France, {NB_JOURS_INITIAL} jours, decoupage adaptatif)")
    debut = datetime.now()
    fin = debut + timedelta(days=NB_JOURS_INITIAL)

    all_events = fetch_range_recursif(debut, fin)

    events_uniques = {e["uid"]: e for e in all_events}.values()
    print(f"\n{len(events_uniques)} evenements uniques recuperes (sur {len(all_events)} avant dedoublonnage).")
    return list(events_uniques)[:MAX_EVENTS]


def save_raw(events):
    os.makedirs(os.path.dirname(PIPELINE_RAW_JSON), exist_ok=True)
    with open(PIPELINE_RAW_JSON, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"Donnees brutes sauvegardees : {PIPELINE_RAW_JSON}")


if __name__ == "__main__":
    since = get_last_import_timestamp()
    events = fetch_events(since)
    save_raw(events)