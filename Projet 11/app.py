import json
import os
import streamlit as st
from chatbot import load_index, build_rag_chatbot, get_chatbot_response
from datetime import datetime
from config import FEEDBACK_JSON


# Sauvegarde du feedback utilisateur
def save_feedback(question, response, feedback):
    feedback_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "question": question,
        "response": response,
        "feedback": feedback
    }

    data = []

    if os.path.exists(FEEDBACK_JSON):
        with open(FEEDBACK_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

    data.append(feedback_data)

    with open(FEEDBACK_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Puls-Events Chatbot",
    page_icon="🎉",
    layout="centered"
)


# Chargement du chatbot
@st.cache_resource
def init_chatbot():
    index, metadatas = load_index()
    chain = build_rag_chatbot()
    return index, metadatas, chain

# Interface utilisateur
st.title("Puls-Events")
st.subheader("Votre assistant pour trouver des événements culturels en Gironde")
st.markdown("Posez vos questions sur les événements culturels en Gironde !")

# Initialisation de l'historique des conversations
if "messages" not in st.session_state:
    st.session_state.messages = []

# Chargement du chatbot
with st.spinner("Chargement du chatbot..."):
    index, metadatas, chain = init_chatbot()

# Affichage de l'historique des conversations
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Saisie de la question de l'utilisateur
if question := st.chat_input("Posez votre question sur les événements en Gironde..."):

    # Affichage de la question de l'utilisateur
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    # Génération de la réponse du chatbot
    with st.chat_message("assistant"):
        with st.spinner("Recherche en cours..."):
            response = get_chatbot_response(index, metadatas, question, chain)
        st.markdown(response)
        col1, col2, _ = st.columns([1, 1, 8])
        with col1:
            if st.button("👍", key=f"pos_{len(st.session_state.messages)}"):
                save_feedback(question, response, "positif")
                st.success("Merci pour votre retour !")
        with col2:
            if st.button("👎", key=f"neg_{len(st.session_state.messages)}"):
                save_feedback(question, response, "negatif")
                st.warning("Merci, nous allons améliorer ça !")
    st.session_state.messages.append({"role": "assistant", "content": response})
