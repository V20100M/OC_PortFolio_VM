"""
pipeline/send_gold_to_qdrant.py
-----------------------------------
Etape 5 : vectorise les evenements Gold non encore envoyes et les insere
dans Qdrant, par sous-lots avec confirmation immediate (un evenement est
marque sent_to_qdrant=TRUE des que son sous-lot est confirme dans Qdrant).
Une interruption (429, coupure reseau...) ne fait donc perdre que le
sous-lot en cours. Relancer le script reprend exactement ou il s'est
arrete, grace au flag sent_to_qdrant deja utilise pour l'incremental.
"""

import time
import uuid
import hashlib
from mistralai.client import Mistral
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.database import get_connection, get_dict_cursor
from scripts.vectorize import build_text
from vectorize_qdrant import get_qdrant_client
from config import MISTRAL_API_KEY, EMBEDDING_MODEL, QDRANT_COLLECTION, CHUNK_SIZE, CHUNK_OVERLAP


EVENTS_PER_BATCH = 200   # evenements traites et commites ensemble avant de passer aux suivants
EMBED_BATCH_SIZE = 50    # taille des appels a l'API Mistral embeddings
MAX_RETRIES = 6          # tentatives avant abandon d'un lot d'embeddings


def deterministic_point_id(uid, chunk_index):
    """ID stable : un rejeu du meme evenement met a jour son point Qdrant
    au lieu d'en creer un doublon."""
    raw = f"{uid}_{chunk_index}"
    return str(uuid.UUID(hashlib.md5(raw.encode()).hexdigest()))


def fetch_unsent_gold():
    conn = get_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM evenements_gold WHERE sent_to_qdrant = FALSE")
            return cur.fetchall()
    finally:
        conn.close()


def build_chunks_and_metadata(rows):
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks, metadatas = [], []

    for row in rows:
        text = build_text(row)
        for i, chunk in enumerate(splitter.split_text(text)):
            chunks.append(chunk)
            metadatas.append({
                "uid": str(row.get("uid", "")),
                "title_fr": str(row.get("title_fr", "")),
                "location_city": str(row.get("location_city", "")),
                "location_department": str(row.get("location_department", "")),
                "location_region": str(row.get("location_region", "")),
                "location_address": str(row.get("location_address", "")),
                "firstdate_begin": str(row.get("firstdate_begin", "")),
                "lastdate_end": str(row.get("lastdate_end", "")),
                "chunk_index": i,
                "text": chunk,
            })

    return chunks, metadatas


def get_embeddings_robust(chunks):
    """Version avec backoff exponentiel (10s, 20s, 40s, 80s, 120s max),
    jusqu'a MAX_RETRIES tentatives par lot, pour absorber les erreurs
    429 'tier capacity exceeded' qui surviennent par vagues."""
    client = Mistral(api_key=MISTRAL_API_KEY)
    all_embeddings = []

    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        attempt = 0
        while True:
            try:
                response = client.embeddings.create(model=EMBEDDING_MODEL, inputs=batch)
                all_embeddings.extend([item.embedding for item in response.data])
                break
            except Exception as e:
                attempt += 1
                if attempt > MAX_RETRIES:
                    raise
                wait = min(10 * (2 ** (attempt - 1)), 120)
                print(f"      Erreur embed (tentative {attempt}/{MAX_RETRIES}) : {e}")
                print(f"      Pause de {wait}s avant nouvelle tentative...")
                time.sleep(wait)
        time.sleep(2)

    return all_embeddings


def ensure_collection(client, dimension):
    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
        print(f"Collection '{QDRANT_COLLECTION}' creee (dimension {dimension}).")


def mark_as_sent(uids):
    if not uids:
        return
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE evenements_gold SET sent_to_qdrant = TRUE WHERE uid = ANY(%s)", (uids,))
    finally:
        conn.close()


def send_gold_to_qdrant():
    rows = fetch_unsent_gold()
    if not rows:
        print("Aucun evenement Gold en attente d'envoi vers Qdrant.")
        return

    total = len(rows)
    nb_lots = -(-total // EVENTS_PER_BATCH)
    print(f"{total} evenements Gold a vectoriser, par sous-lots de {EVENTS_PER_BATCH} ({nb_lots} sous-lots).")

    client = get_qdrant_client()
    collection_prete = False
    traites = 0

    for i in range(0, total, EVENTS_PER_BATCH):
        sous_lot = rows[i:i + EVENTS_PER_BATCH]
        print(f"\n  Sous-lot {i // EVENTS_PER_BATCH + 1}/{nb_lots} ({len(sous_lot)} evenements)...")

        chunks, metadatas = build_chunks_and_metadata(sous_lot)
        embeddings = get_embeddings_robust(chunks)

        if not collection_prete:
            ensure_collection(client, dimension=len(embeddings[0]))
            collection_prete = True

        points = [
            PointStruct(id=deterministic_point_id(m["uid"], m["chunk_index"]), vector=v, payload=m)
            for m, v in zip(metadatas, embeddings)
        ]
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)

        mark_as_sent([row["uid"] for row in sous_lot])
        traites += len(sous_lot)
        print(f"  {traites}/{total} evenements confirmes dans Qdrant.")

    print(f"\nTermine : {traites} evenements envoyes dans Qdrant.")


if __name__ == "__main__":
    send_gold_to_qdrant()