import time
import faiss
import json
import os
import numpy as np
from config import MISTRAL_API_KEY, EMBEDDING_MODEL, LLM_MODEL, TOP_K, GEO_FILTER_FIELD, GEO_FILTER_VALUE, get_geo_paths
from mistralai.client import Mistral
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, chain
from langchain_core.output_parsers import StrOutputParser


# Chargement de l'index Faiss et des métadonnées
def load_index(faiss_index_path=None, faiss_metadatas_path=None):
    if faiss_index_path is None or faiss_metadatas_path is None:
        default_paths = get_geo_paths(GEO_FILTER_FIELD, GEO_FILTER_VALUE)
        faiss_index_path = faiss_index_path or default_paths["faiss_index"]
        faiss_metadatas_path = faiss_metadatas_path or default_paths["faiss_metadatas"]

    index = faiss.read_index(faiss_index_path)
    with open(faiss_metadatas_path, "r", encoding="utf-8") as f:
        metadatas = json.load(f)
        print(f"Index chargé avec {index.ntotal} vecteurs")
        print(f"Métadonnées chargées : {len(metadatas)} chunks")
    return index, metadatas


# Recherche sémantique dans Faiss
def search_faiss(index, metadatas, query, top_k=TOP_K):
    client = Mistral(api_key=MISTRAL_API_KEY)

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        inputs=[query]
    )
    query_vector = np.array([response.data[0].embedding], dtype=np.float32)
    faiss.normalize_L2(query_vector)

    distances, indices = index.search(query_vector, top_k)

    results = []
    for idx, score in zip(indices[0], distances[0]):
        meta = metadatas[idx]
        results.append({
            "score": float(score),
            "title": meta.get("title_fr", ""),
            "city": meta.get("location_city", ""),
            "address": meta.get("location_address", ""),
            "firstdate_begin": meta.get("firstdate_begin", ""),
            "lastdate_end": meta.get("lastdate_end", ""),
            "text": meta.get("text", "")
        })

    return results


# Construction du contexte pour le LLM
def build_context(results):
    context_parts = []
    for i, r in enumerate(results):
        context_parts.append(
            f"Événement {i+1} :\n"
            f"  Titre: {r['title']}\n"
            f"  Ville: {r['city']}\n"
            f"  Adresse: {r['address']}\n"
            f"  Date de début: {r['firstdate_begin']}\n"
            f"  Date de fin: {r['lastdate_end']}\n"
            f"  Détails: {r['text']}\n"
        )
    return "\n".join(context_parts)


# Chatbot RAG
def build_rag_chatbot(location_label=None):
    location_label = location_label or GEO_FILTER_VALUE

    llm = ChatMistralAI(
        model=LLM_MODEL,
        api_key=MISTRAL_API_KEY,
        temperature=0.3
    )

    prompt = PromptTemplate(
        input_variables=["context", "location_label", "question"],
        template="""Tu es un assistant spécialisé dans la recherche d'événements culturels à {location_label}.
        Réponds à la question de l'utilisateur en te basant uniquement sur les informations fournies dans le contexte.
        Si tu ne trouves pas d'événement pertinent, dis simplement que tu n'as pas cette information.
        Réponds toujours en français, de manière concise et utile.

        Contexte - Evénements disponibles : {context}

        Question de l'utilisateur : {question}

        Réponse : """
    )

    # .partial() fixe location_label dès la construction de la chaîne :
    # chain.invoke() n'aura besoin de fournir que context/question ensuite.
    prompt = prompt.partial(location_label=location_label)

    chain = prompt | llm | StrOutputParser()
    return chain


# Réponse du chatbot
def get_chatbot_response(index, metadatas, question, chain):
    max_retries = 10
    for attempt in range(max_retries):
        try:
            results = search_faiss(index, metadatas, question)
            context = build_context(results)
            response = chain.invoke({"context": context, "question": question})
            return response
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                print(f"Rate limit atteint, pause de 10s ... (tentative {attempt + 1}/{max_retries})")
                time.sleep(10)
            else:
                raise e


# Interface en ligne de commande
def main():
    print("Chargement du chatbot...")
    index, metadatas = load_index()
    chain = build_rag_chatbot()

    print(f"\nChatbot Puls-Events prêt à répondre à vos questions sur les événements culturels en {GEO_FILTER_VALUE} !")
    print("Posez vos questions (ou tapez 'quitter' pour quitter) :")

    while True:
        question = input("Vous : ").strip()

        if not question:
            print("Veuillez entrer une question ou 'quitter' pour sortir.")
            continue

        if question.lower() in ["exit", "quit", "quitter"]:
            print("Au revoir !")
            break

        print("Assistant : ", end="", flush=True)
        response = get_chatbot_response(index, metadatas, question, chain)
        print(f"Réponse du chatbot : {response}\n")
        print()


if __name__ == "__main__":
    main()