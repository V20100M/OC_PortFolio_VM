import faiss
import json
import os
import numpy as np
from config import MISTRAL_API_KEY, EMBEDDING_MODEL, LLM_MODEL, TOP_K, FAISS_INDEX, FAISS_METADATAS
from mistralai.client import Mistral
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, chain
from langchain_core.output_parsers import StrOutputParser


# Chargement de l'index Faiss et des métadonnées
def load_index():
    index = faiss.read_index(FAISS_INDEX)
    with open(FAISS_METADATAS, "r", encoding="utf-8") as f:
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
def build_rag_chatbot():
    llm = ChatMistralAI(
        model=LLM_MODEL,
        api_key=MISTRAL_API_KEY,
        temperature=0.3
    )

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""Tu es un assistant spécialisé dans la recherche d'événements culturels en Gironde.
        Réponds à la question de l'utilisateur en te basant uniquement sur les informations fournies dans le contexte.
        Si tu ne trouves pas d'événement pertinent, dis simplement que tu n'as pas cette information.
        Réponds toujours en français, de manière concise et utile.

        Contexte - Evénements disponibles : {context}

        Question de l'utilisateur : {question}

        Réponse : """
    )

    chain = prompt | llm | StrOutputParser()
    return chain


# Réponse du chatbot
def get_chatbot_response(index, metadatas, question, chain):
    results = search_faiss(index, metadatas, question)
    context = build_context(results)
    response = chain.invoke({"context": context, "question": question})

    return response


# Interface en ligne de commande
def main():
    print("Chargement du chatbot...")
    index, metadatas = load_index()
    chain = build_rag_chatbot()

    print("\nChatbot Puls-Events prêt à répondre à vos questions sur les événements culturels en Gironde !")
    print("Posez vos questions sur les événements en Gironde (ou tapez 'quitter' pour quitter) :")

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
