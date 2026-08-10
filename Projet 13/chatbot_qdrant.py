"""
chatbot_qdrant.py
------------------
Test de faisabilite : recherche semantique via Qdrant (filtrage natif
par payload geographique) au lieu de Faiss (un index par localisation).

Ne modifie ni n'affecte chatbot.py.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from mistralai.client import Mistral
from config import MISTRAL_API_KEY, EMBEDDING_MODEL, TOP_K, QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
from chatbot import build_rag_chatbot


def get_qdrant_client():
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def search_qdrant(client, query, geo_field, geo_value, top_k=TOP_K):
    mistral_client = Mistral(api_key=MISTRAL_API_KEY)
    response = mistral_client.embeddings.create(model=EMBEDDING_MODEL, inputs=[query])
    query_vector = response.data[0].embedding

    query_filter = Filter(
        must=[FieldCondition(key=geo_field, match=MatchValue(value=geo_value))]
    )

    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
    )

    return [
        {
            "score": point.score,
            "title": point.payload.get("title_fr", ""),
            "city": point.payload.get("location_city", ""),
            "department": point.payload.get("location_department", ""),
            "region": point.payload.get("location_region", ""),
            "address": point.payload.get("location_address", ""),
            "firstdate_begin": point.payload.get("firstdate_begin", ""),
            "lastdate_end": point.payload.get("lastdate_end", ""),
            "text": point.payload.get("text", ""),
        }
        for point in results.points
    ]


def get_chatbot_response_qdrant(client, question, chain, geo_field, geo_value):
    results = search_qdrant(client, question, geo_field, geo_value)
    context = build_context_qdrant(results)
    return chain.invoke({"context": context, "question": question})


def build_context_qdrant(results):
    context_parts = []
    for i, r in enumerate(results):
        context_parts.append(
            f"Événement {i+1} :\n"
            f"  Titre: {r['title']}\n"
            f"  Ville: {r['city']}\n"
            f"  Département: {r['department']}\n"
            f"  Région: {r['region']}\n"
            f"  Adresse: {r['address']}\n"
            f"  Date de début: {r['firstdate_begin']}\n"
            f"  Date de fin: {r['lastdate_end']}\n"
            f"  Détails: {r['text']}\n"
        )
    return "\n".join(context_parts)


def main():
    print("=== Test de faisabilite Qdrant : une seule collection, 3 granularites ===\n")
    client = get_qdrant_client()
    chain = build_rag_chatbot(location_label="zone testee")

    tests = [
        ("location_city", "Mérignac", "Quels evenements a Merignac ?"),
        ("location_department", "Gironde", "Quels evenements en Gironde ?"),
        ("location_region", "Nouvelle-Aquitaine", "Quels evenements en Nouvelle-Aquitaine ?"),
    ]

    for geo_field, geo_value, question in tests:
        print(f"--- Filtre : {geo_field} = {geo_value} ---")
        print(f"Q: {question}")
        response = get_chatbot_response_qdrant(client, question, chain, geo_field, geo_value)
        print(f"R: {response}\n")


if __name__ == "__main__":
    main()