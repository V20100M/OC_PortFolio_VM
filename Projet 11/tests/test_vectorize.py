import faiss
import json
import numpy as np
import pytest
from mistralai.client import Mistral
from config import MISTRAL_API_KEY, EMBEDDING_MODEL, TOP_K, FAISS_INDEX, FAISS_METADATAS


# Fixture pour charger l'index Faiss et les métadonnées avant les tests
@pytest.fixture
def index_and_metadatas():
    """Charge l'index Faiss et les métadonnées pour les tests"""
    index = faiss.read_index(FAISS_INDEX)
    with open(FAISS_METADATAS, 'r', encoding="utf-8") as f:
        metadatas = json.load(f)
    return index, metadatas


# TESTS
def test_index_non_vide(index_and_metadatas):
    """Vérifie que l'index Faiss contient des vecteurs"""
    index, _ = index_and_metadatas
    assert index.ntotal > 0, "L'index Faiss est vide"

def test_metadatas_non_vides(index_and_metadatas):
    """Vérifie que les métadonnées contiennent des chunks"""
    _, metadatas = index_and_metadatas
    assert len(metadatas) > 0, "Les métadonnées sont vides"

def test_aucun_chunk_vide(index_and_metadatas):
    """Vérifie que les métadonnées ne contiennent pas de chunks vides"""
    _, metadatas = index_and_metadatas
    chunks_vides = [m for m in metadatas if not m.get("text", "").strip()]
    assert len(chunks_vides) == 0, f"{len(chunks_vides)} chunks vides trouvés dans les métadonnées"

def test_coherence_index_metadatas(index_and_metadatas):
    """Vérifie que le nombre de vecteurs dans l'index correspond au nombre de métadonnées"""
    index, metadatas = index_and_metadatas
    assert index.ntotal == len(metadatas), \
        f"Nombre de vecteurs ({index.ntotal}) ne correspond pas au nombre de métadonnées ({len(metadatas)})"

def test_metadatas_champs_requis(index_and_metadatas):
    """Vérifie que les métadonnées contiennent les champs obligatoires pour la construction du contexte"""
    _, metadatas = index_and_metadatas
    champs_requis = ["uid", "title_fr", "location_city", "firstdate_begin", "lastdate_end", "text"]
    for meta in metadatas:
        for champ in champs_requis:
            assert champ in meta, f"Le champ {champ} est manquant."

def test_pertinence_recherche(index_and_metadatas):
    """Vérifie que la recherche sémantique retourne des résultats cohérents et pertinents"""
    index, metadatas = index_and_metadatas
    client = Mistral(api_key=MISTRAL_API_KEY)
    query = "Concert de musique à Bordeaux"

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        inputs=[query]
    )
    query_vector = np.array([response.data[0].embedding], dtype=np.float32)
    faiss.normalize_L2(query_vector)

    distances, indices = index.search(query_vector, TOP_K)

    # Vérifications basiques sur les résultats
    assert len(indices[0]) == TOP_K, f"Nombre de résultats incorrect : {len(indices[0])} au lieu de {TOP_K}"
    for score in distances[0]:
        assert 0 <= score <= 1, f"Score hors limites : {score}"

    # Vérification de la pertinence des résultats
    mots_cles_concert = ["concert", "musique", "music", "jazz", "rock", "chanson", "orchestre", "scène"]
    mots_cles_localisation = ["bordeaux", "gironde", "aquitaine", "nouvelle-aquitaine"]

    resultats_pertinents = sum(
        1 for idx in indices[0]
        if any(mot in (metadatas[idx].get("title_fr", "") + " " + metadatas[idx].get("text", "")).lower()
            for mot in mots_cles_concert)
        and any(loc in (metadatas[idx].get("location_city", "") + " " + metadatas[idx].get("text", "")).lower()
                for loc in mots_cles_localisation)
    )
    assert resultats_pertinents >= TOP_K // 2, \
        f"Seulements {resultats_pertinents} résultats pertinents trouvés pour la requête de test"

    print(f"\nTop {TOP_K} résultats pour la requête '{query}' :")
    for rank, (idx, score) in enumerate(zip(indices[0], distances[0])):
        meta = metadatas[idx]
        print(f" Rank {rank+1} - Score: {score:.3f} - {meta['title_fr']} - {meta['location_city']}")
