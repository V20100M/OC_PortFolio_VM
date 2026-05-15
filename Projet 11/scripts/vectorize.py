import faiss
import json
import os
import numpy as np
import pandas as pd
import time
from mistralai.client import Mistral
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import MISTRAL_API_KEY, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, EVENTS_CSV, EMBEDDINGS_NPY, FAISS_INDEX, FAISS_METADATAS


# Chargement des données
def load_events():
    df = pd.read_csv(EVENTS_CSV)
    print(f"Événements chargés : {len(df)}")
    return df


# Construction du texte à vectoriser
def build_text(row):
    parts = [
        f"Titre: {row.get('title_fr', '')}",
        f"Description: {row.get('description_fr', '')}",
        f"Description longue: {row.get('longdescription_fr', '')}",
        f"Lieu: {row.get('location_name', '')} - {row.get('location_city', '')}",
        f"Date de début: {row.get('firstdate_begin', '')}",
        f"Date de fin: {row.get('lastdate_end', '')}",
    ]
    return "\n".join([p for p in parts if p.split(": ", 1)[-1].strip()])


# Découpage du texte en chunks
def split_into_chunks(df):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

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
                "location_address": str(row.get("location_address", "")),
                "firstdate_begin": str(row.get("firstdate_begin", "")),
                "lastdate_end": str(row.get("lastdate_end", "")),
                "chunk_index": i,
                "text": chunk
            })

    print(f"Chunks créés : {len(chunks)}")
    return chunks, metadatas


# Vectorisation par batch
def get_embeddings(chunks, batch_size=50):
    client = Mistral(api_key=MISTRAL_API_KEY)
    all_embeddings = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                inputs=batch
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
            print(f" Vectorisés : {min(i + batch_size, len(chunks))} / {len(chunks)}", end="\r")
            time.sleep(5)  # Petite pause pour éviter de surcharger l'API
        except Exception as e:
            print(f"Erreur batch {i//batch_size + 1} : {e}")
            print("Pause de 10 secondes avant de continuer...")
            time.sleep(10)

            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                inputs=batch
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)


    print(f"\nVectorisation terminée : {len(all_embeddings)} vecteurs générés.")
    return all_embeddings


# Indexation avec Faiss
def build_faiss_index(embeddings):
    vectors = np.array(embeddings, dtype='float32')
    dimension = vectors.shape[1]

    # Index
    index = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    print(f"Index Faiss créé avec {index.ntotal} vecteurs et dimension {dimension}.")
    return index


# Sauvegarde des vecteurs et métadonnées
def save(index, metadatas):
    faiss.write_index(index, FAISS_INDEX)
    with open(FAISS_METADATAS, 'w', encoding="utf-8") as f:
        json.dump(metadatas, f, ensure_ascii=False, indent=2)
    print("Index et métadonnées sauvegardés : faiss_index.bin et faiss_metadatas.json")



# Main
if __name__ == "__main__":
    df = load_events()
    chunks, metadatas = split_into_chunks(df)

    if os.path.exists(EMBEDDINGS_NPY):
        print("Chargement des embeddings depuis embeddings.npy...")
        embeddings = np.load(EMBEDDINGS_NPY).tolist()
    else:
        embeddings = get_embeddings(chunks)

        # Sauvegarde des embeddings intermédiaires pour éviter de tout refaire en cas de problème
        np.save(EMBEDDINGS_NPY, np.array(embeddings, dtype='float32'))
        print(f"Embeddings sauvegardés dans {EMBEDDINGS_NPY}")

    index = build_faiss_index(embeddings)
    save(index, metadatas)
    print("Processus de vectorisation et d'indexation terminé avec succès.")