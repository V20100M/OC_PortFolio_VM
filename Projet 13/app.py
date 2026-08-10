import os
import uuid
import requests
import streamlit as st
from config import GEO_LEVELS, API_BASE_URL
from geolocation import detect_browser_ip_location, resolve_commune, search_communes


def ask_backend(message, geo_field, geo_value, ville_initiale, conversation_id):
    """Appelle l'endpoint /chat du backend FastAPI (logique centralisée, partagée avec le popup)."""
    response = requests.post(
        f"{API_BASE_URL}/chat",
        json={
            "message": message,
            "geo_field": geo_field,
            "geo_value": geo_value,
            "ville_initiale": ville_initiale,
            "conversation_id": conversation_id,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def send_feedback(interaction_id, feedback):
    """Envoie le feedback au backend, centralise avec latence/source/etc. (table interactions_log)."""
    if interaction_id is None:
        return False
    try:
        response = requests.post(
            f"{API_BASE_URL}/feedback",
            json={"interaction_id": interaction_id, "feedback": feedback},
            timeout=10,
        )
        return response.ok
    except Exception:
        return False


st.set_page_config(
    page_title="Puls-Events Chatbot",
    page_icon="🎉",
    layout="centered"
)

st.title("Puls-Events")

if "geo_confirmed" not in st.session_state:
    st.session_state.geo_confirmed = False
if "geo_field" not in st.session_state:
    st.session_state.geo_field = None
if "geo_value" not in st.session_state:
    st.session_state.geo_value = None
if "ville_initiale" not in st.session_state:
    st.session_state.ville_initiale = None
if "commune_resolue" not in st.session_state:
    st.session_state.commune_resolue = None
if "commune_validee" not in st.session_state:
    st.session_state.commune_validee = False
if "correction_manuelle" not in st.session_state:
    st.session_state.correction_manuelle = False
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []


if not st.session_state.geo_confirmed:
    st.subheader("Localisons-vous pour affiner vos recommandations")

    if st.session_state.commune_resolue is None and not st.session_state.correction_manuelle:
        ip_location = detect_browser_ip_location()
        if ip_location and ip_location.get("city"):
            resolved = resolve_commune(ip_location["city"])
            if resolved:
                st.session_state.commune_resolue = resolved

    if st.session_state.commune_resolue and not st.session_state.commune_validee and not st.session_state.correction_manuelle:
        ville = st.session_state.commune_resolue["ville"]
        st.write(f"Nous vous situons à **{ville}**. Est-ce correct ?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Oui, c'est correct"):
                st.session_state.commune_validee = True
                st.rerun()
        with col2:
            if st.button("Non, corriger"):
                st.session_state.commune_resolue = None
                st.session_state.commune_validee = False
                st.session_state.correction_manuelle = True
                st.rerun()

    if st.session_state.correction_manuelle or (
        st.session_state.commune_resolue is None and not st.session_state.commune_validee
    ):
        st.write("Indiquez votre ville :")
        recherche = st.text_input("Nom de la ville", key="recherche_ville")
        if recherche:
            resultats = search_communes(recherche, limit=8)
            if resultats:
                options = [r["nom"] for r in resultats]
                choix = st.selectbox("Sélectionnez votre ville", options, key="choix_ville")
                if st.button("Valider cette ville"):
                    st.session_state.commune_resolue = resolve_commune(choix)
                    st.session_state.commune_validee = True
                    st.session_state.correction_manuelle = False
                    st.rerun()
            else:
                st.info("Aucune commune trouvée, vérifiez l'orthographe.")

    if st.session_state.commune_resolue and st.session_state.commune_validee:
        commune = st.session_state.commune_resolue
        st.write(
            f"Ville : **{commune['ville']}** — "
            f"Département : **{commune['departement']}** — "
            f"Région : **{commune['region']}**"
        )

        niveau = st.radio(
            "Dans quel rayon souhaitez-vous rechercher des événements ?",
            options=list(GEO_LEVELS.keys()),
            index=1,
        )

        valeur_par_niveau = {
            "Ville": commune["ville"],
            "Département": commune["departement"],
            "Région": commune["region"],
        }

        if st.button("Rechercher les événements"):
            st.session_state.geo_field = GEO_LEVELS[niveau]
            st.session_state.geo_value = valeur_par_niveau[niveau]
            st.session_state.ville_initiale = commune["ville"]
            st.session_state.conversation_id = str(uuid.uuid4())
            st.session_state.geo_confirmed = True
            st.rerun()

    st.stop()


st.subheader(f"Votre assistant pour trouver des événements culturels — {st.session_state.geo_value}")
st.markdown("Posez vos questions sur les événements culturels dans votre zone !")

if st.button("Changer de localisation", key="reset_geo"):
    for key in ["geo_confirmed", "geo_field", "geo_value", "ville_initiale", "commune_resolue",
                "commune_validee", "correction_manuelle", "conversation_id", "messages"]:
        st.session_state.pop(key, None)
    st.rerun()

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("interaction_id") is not None:
            col1, col2, _ = st.columns([1, 1, 8])
            with col1:
                if st.button("👍", key=f"pos_{i}"):
                    if send_feedback(message["interaction_id"], "positif"):
                        st.success("Merci pour votre retour !")
            with col2:
                if st.button("👎", key=f"neg_{i}"):
                    if send_feedback(message["interaction_id"], "negatif"):
                        st.warning("Merci, nous allons améliorer ça !")

if question := st.chat_input("Posez votre question sur les événements..."):

    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        with st.spinner("Recherche en cours... (peut prendre plus de temps si la recherche web est necessaire)"):
            interaction_id = None
            try:
                result = ask_backend(
                    question,
                    st.session_state.geo_field,
                    st.session_state.geo_value,
                    st.session_state.ville_initiale,
                    st.session_state.conversation_id,
                )
                response = result["response"]
                st.session_state.conversation_id = result["conversation_id"]
                interaction_id = result.get("interaction_id")
            except Exception:
                response = "Désolé, une erreur est survenue lors de la génération de la réponse."
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response, "interaction_id": interaction_id})
    st.rerun()