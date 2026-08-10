"""
routers/chat.py
----------------
Endpoint de conversation avec le chatbot RAG basé sur Qdrant.
Centralise la logique partagée entre Streamlit (dev) et le popup web (prod).
Repli automatique sur la recherche web (smolagents/Tavily) si la base
vectorielle ne trouve rien de pertinent.
"""

import os
import logging
import time
import uuid
from typing import Optional
from fastapi import APIRouter, Header
from utils.logging_utils import get_domain_logger
from backend.schemas import ChatRequest, ChatResponse, FeedbackRequest
from backend.security import decode_access_token
from backend.database import get_connection
from chatbot import build_rag_chatbot
from chatbot_qdrant import get_qdrant_client, get_chatbot_response_qdrant
from websearch_agent import get_websearch_response

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = get_domain_logger("chat", "chat.log", BASE_DIR)

router = APIRouter(tags=["chat"])

# Client Qdrant et chaine LangChain construits une seule fois au demarrage
# du backend. Plus de reconstruction par requete ni par localisation,
# contrairement a l'ancienne approche Faiss (un index par zone).
_qdrant_client = get_qdrant_client()
_chain = build_rag_chatbot(location_label="la zone demandee")


def _get_user_from_token(authorization: Optional[str]):
    """Décode le token JWT si présent. Retourne None si absent/invalide (utilisateur invité)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_access_token(token)
    except Exception:
        logger.warning("Token invalide ou expiré reçu sur /chat")
        return None


def _save_exchange(id_utilisateur, conversation_id, role, texte):
    """
    N'interrompt JAMAIS la requête en cas d'échec (utile tant que PostgreSQL n'est pas encore connecté).
    """
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO historiques_chatbot (id_utilisateur, conversation_id, role, texte)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (id_utilisateur, conversation_id, role, texte),
                )
        conn.close()
    except Exception as e:
        logger.warning("Historique non sauvegardé (PostgreSQL indisponible ?) : %s", e)


def _log_interaction(id_utilisateur, conversation_id, question, reponse,
                      ville_initiale, geo_field, geo_value, source_reponse, latence_ms):
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO interactions_log
                        (id_utilisateur, conversation_id, question, reponse,
                         ville_initiale, geo_field, geo_value, source_reponse, latence_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (id_utilisateur, conversation_id, question, reponse,
                     ville_initiale, geo_field, geo_value, source_reponse, latence_ms),
                )
                interaction_id = cur.fetchone()[0]
        conn.close()
        return interaction_id
    except Exception as e:
        logger.warning("Log d'interaction non sauvegarde : %s", e)
        return None


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, authorization: Optional[str] = Header(default=None)):
    user = _get_user_from_token(authorization)
    id_utilisateur = user["id_utilisateur"] if user else None

    conversation_id = payload.conversation_id or str(uuid.uuid4())
    debut = time.time()
    source_reponse = "qdrant"

    try:
        response_text = get_chatbot_response_qdrant(
            _qdrant_client, payload.message, _chain, payload.geo_field, payload.geo_value
        )
    except Exception as e:
        logger.error("Erreur lors de la génération de la réponse : %s", e)
        response_text = "Désolé, une erreur est survenue lors de la génération de la réponse."

    # Repli recherche web si la base vectorielle n'a rien trouve de pertinent
    signaux_absence = ["je n'ai pas cette information", "je n'ai pas d'information", "aucun événement"]
    if any(signal in response_text.lower() for signal in signaux_absence):
        logger.info("Aucun resultat pertinent en base, repli sur la recherche web (smolagents)")
        try:
            response_text = get_websearch_response(payload.message, payload.geo_value)
            source_reponse = "web_search"
        except Exception as e:
            logger.warning("Echec de la recherche web (smolagents) : %s", e)

    latence_ms = int((time.time() - debut) * 1000)

    _save_exchange(id_utilisateur, conversation_id, "utilisateur", payload.message)
    _save_exchange(id_utilisateur, conversation_id, "assistant", response_text)

    interaction_id = _log_interaction(
        id_utilisateur, conversation_id, payload.message, response_text,
        payload.ville_initiale, payload.geo_field, payload.geo_value,
        source_reponse, latence_ms,
    )

    return ChatResponse(response=response_text, conversation_id=conversation_id, interaction_id=interaction_id)


@router.post("/feedback")
def feedback(payload: FeedbackRequest):
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE interactions_log SET feedback = %s WHERE id = %s",
                    (payload.feedback, payload.interaction_id),
                )
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        logger.warning("Feedback non sauvegarde : %s", e)
        return {"status": "erreur"}