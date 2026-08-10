"""
vectorize_qdrant.py
--------------------
Test de faisabilite : vectorisation et indexation des evenements dans
Qdrant, avec filtrage geographique natif (payload) au lieu d'un index
Faiss separe par localisation.

Ne modifie ni n'affecte le pipeline Faiss existant (vectorize.py).
"""

import os
import uuid
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, CHUNK_SIZE, CHUNK_OVERLAP
from scripts.vectorize import load_events, build_text, get_embeddings


def get_qdrant_client():
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def split_into_chunks_qdrant(df):
    """
    Identique a split_into_chunks() de vectorize.py, avec les champs
    location_department et location_region en plus dans les metadonnees
    (necessaires pour le filtrage multi-granularite dans Qdrant).
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = []
    metadatas = []

    for _, row in df.iterrows():
        text = build_text(row)
        splits = splitter.split_text(text)

        for i, chunk in enumerate(splits):
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

    print(f"Chunks crees (Qdrant) : {len(chunks)}")
    return chunks, metadatas


def create_collection(client, dimension):
    client.recreate_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
    )
    print(f"Collection '{QDRANT_COLLECTION}' creee (dimension {dimension}).")


def upsert_events(client, metadatas, embeddings):
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=vector, payload=meta)
        for meta, vector in zip(metadatas, embeddings)
    ]

    batch_size = 100
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=QDRANT_COLLECTION, points=points[i:i + batch_size])
        print(f"  Envoyes : {min(i + batch_size, len(points))} / {len(points)}", end="\r")

    print(f"\n{len(points)} points envoyes dans Qdrant.")


def run_qdrant_ingestion(events_csv, embeddings_npy_cache=None):
    df = load_events(events_csv)
    chunks, metadatas = split_into_chunks_qdrant(df)

    # Reutilise le cache d'embeddings Faiss existant si disponible (memes
    # chunks, meme decoupage) pour eviter de repayer/reattendre Mistral.
    if embeddings_npy_cache and os.path.exists(embeddings_npy_cache):
        print(f"Reutilisation du cache d'embeddings existant : {embeddings_npy_cache}")
        embeddings = np.load(embeddings_npy_cache).tolist()
    else:
        embeddings = get_embeddings(chunks)

    client = get_qdrant_client()
    dimension = len(embeddings[0])
    create_collection(client, dimension)
    upsert_events(client, metadatas, embeddings)


if __name__ == "__main__":
    from config import get_geo_paths, GEO_FILTER_FIELD, GEO_FILTER_VALUE
    paths = get_geo_paths(GEO_FILTER_FIELD, GEO_FILTER_VALUE)
    run_qdrant_ingestion(paths["events_csv"], embeddings_npy_cache=paths["embeddings_npy"])