"""
consumer_slack.py
------------------
Lit les nouveaux messages du topic Kafka/Redpanda 'sport.public.strava'
(produits par Debezium CDC) et envoie une notification Slack pour
chaque nouvelle activite sportive enregistree.

Mode batch : se connecte, traite les messages disponibles, puis s'arrete
apres consumer_timeout_ms sans nouveau message.
Conçu pour être déclenché périodiquement par Kestra.

Flux :
  Redpanda (topic sport.public.strava)
  - lecture du message Debezium (payload.after)
  - récupération du salarié associé (PostgreSQL)
  - récupération du commentaire Strava (strava_comment)
  - formatage du message
  - envoi webhook Slack
"""

import os
import sys
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from kafka import KafkaConsumer

from utils.config import BASE_DIR, SLACK_WEBHOOK_URL, KAFKA_BOOTSTRAP_SERVERS, SPORT_ARTICLES
from utils.db import get_connection
from utils.logging_utils import setup_logging
from utils.strava_generation import normalize_sport



# ---------------------------------------------------------------------------
# Logging UTF-8 robuste (IDEs, pytest, redirection)
# ---------------------------------------------------------------------------
setup_logging("consumer_slack.log", BASE_DIR)
logger = logging.getLogger(__name__)



TOPIC = "sport.public.strava"
GROUP_ID = "slack-notifier"
CONSUMER_TIMEOUT_MS = 5000



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def validate_config():
    """
    Vérifie que les variables de configuration critiques sont présentes.
    Lève une EnvironmentError au démarrage si SLACK_WEBHOOK_URL est absent,
    plutôt que d'échouer silencieusement au moment de l'envoi.
    """
    if not SLACK_WEBHOOK_URL:
        raise EnvironmentError(
            "SLACK_WEBHOOK_URL est absent ou vide. "
            "Vérifiez les secrets Kestra ou le fichier .env."
        )
    logger.info("Configuration validée : SLACK_WEBHOOK_URL présent")


def get_sport_article(sport_label):
    """Retourne l'article correct (du/de la/de l') pour un sport donné."""
    key = normalize_sport(sport_label)
    return SPORT_ARTICLES.get(key, "du")


def get_salarie_info(id_strava, conn):
    """Recupere prenom/nom du salarie associe a une activite Strava.
    Retourne :
        (prenom, nom) ou None si aucun salarié trouvé.
    """
    query = """
        SELECT s.prenom, s.nom
        FROM strava st
        JOIN stravathlete sth ON st.id_strava = sth.id_strava
        JOIN salarieathlete ssa ON sth.id_athlete = ssa.id_athlete
        JOIN salarie s ON ssa.id_salarie = s.id_salarie
        WHERE st.id_strava = %s
    """
    with conn.cursor() as cur:
        cur.execute(query, (id_strava,))
        return cur.fetchone()   # (prenom, nom) ou None


def get_comment(id_strava, conn):
    """
    Récupère le commentaire associé à une activité Strava.

    Retourne le texte du premier commentaire (le plus ancien), ou None si absent.
    Un même id_strava peut avoir plusieurs commentaires — on prend le premier
    par cohérence avec le comportement de l'API Strava (premier commentaire affiché).
    """
    query = """
        SELECT texte
        FROM strava_comment
        WHERE id_strava = %s
        ORDER BY created_at ASC
        LIMIT 1;
    """
    with conn.cursor() as cur:
        cur.execute(query, (id_strava,))
        result = cur.fetchone()
        return result[0] if result else None



def format_message(activite, prenom, nom, commentaire=None):
    """Construit le payload JSON du message Slack.*
    Affiche distance, vitesse et puissance uniquement si disponibles
    (certains sports n'ont pas de distance ou de données de puissance).
    Le commentaire Strava est affiché en italique s'il existe.
    """
    duree_min = activite["moving_time"] // 60
    article = get_sport_article(activite["sport_type"])

    text = (
        f"🎉 *Félicitations à {prenom} {nom}* pour avoir fait "
        f"{article} *{activite['sport_type']}* pendant *{duree_min} min* !\n\n"
    )

    if activite["distance"] is not None:
        distance_km = activite["distance"] / 1000
        text += f"📊 Quelques chiffres :\n📏 Distance : {distance_km:.1f} km\n"

    if activite["avg_speed"] is not None:
        avg_speed_kmh = activite["avg_speed"] * 3.6
        text += f"⚡ Vitesse moy. : {avg_speed_kmh:.1f} km/h\n"

    if activite["max_speed"] is not None:
        max_speed_kmh = activite["max_speed"] * 3.6
        text += f"🚀 Pointe max : {max_speed_kmh:.1f} km/h\n"

    if activite["avg_watt"] is not None:
        text += f"⚙️ Puissance moy. : {activite['avg_watt']} W\n"

    if activite["max_watt"] is not None:
        text += f"🔥 Puissance max : {activite['max_watt']} W\n"

    if commentaire:
        text += f"\n💬 _{commentaire}_\n"

    text += "\n💪 Maintenant, à qui le tour ?\n\n\n"

    return {"text": text}


def send_to_slack(message):
    """Envoie le message au webhook Slack.
    Raises:
        requests.HTTPError si la requête échoue (géré par l'appelant).
    """
    response = requests.post(SLACK_WEBHOOK_URL, json=message)
    response.raise_for_status()



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=== Demarrage consumer Slack ===")

    # Validation de la configuration au démarrage
    try:
        validate_config()
    except EnvironmentError as exc:
        logger.critical("%s", exc)
        return

    # Connexion PostgreSQL
    try:
        conn = get_connection()
        logger.info("Connexion PostgreSQL établie")
    except Exception as exc:
        logger.critical("Impossible de se connecter à PostgreSQL : %s", exc)
        return


    # Connexion Kafka/Redpanda
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))  if m is not None else None,
        auto_offset_reset="latest",
        group_id=GROUP_ID,
        enable_auto_commit=True,
        consumer_timeout_ms=CONSUMER_TIMEOUT_MS,
    )

    count = 0
    errors = 0

    try:
        for msg in consumer:
            if msg.value is None:
                continue # Ignore les messages de suppression (tombstones)

            payload = msg.value.get("payload", {})
            activite = payload.get("after")

            if activite is None:
                continue # Ignore les événements qui ne sont pas des insertions

            try:
                salarie = get_salarie_info(activite["id_strava"], conn)
                if salarie is None:
                    logger.warning(
                        "Aucun salarie trouve pour id_strava=%s",
                        activite["id_strava"],
                    )
                    continue

                prenom, nom = salarie
                commentaire = get_comment(activite["id_strava"], conn)
                message = format_message(activite, prenom, nom, commentaire)
                send_to_slack(message)
                logger.info(
                    "Notification envoyée : %s %s — %s",
                    prenom, nom, activite["sport_type"], bool(commentaire)
                )
                count += 1

            except Exception as e:
                logger.error(
                    "Erreur traitement id_strava=%s : %s",
                    activite.get("id_strava"), e,
                )
                errors += 1

    except Exception as exc:
        logger.error("Erreur inattendue dans la boucle consumer : %s", exc)

    finally:
        # Fermeture PostgreSQL et Kafka même en cas d'erreur
        consumer.close()
        logger.info("Consumer Kafka fermé")
        conn.close()
        logger.info("Connexion PostgreSQL fermée")

    logger.info(
        "=== Consumer termine : %d notification(s) envoyee(s), %d erreur(s) ===",
        count, errors,
    )


if __name__ == "__main__":
    main()