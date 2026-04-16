import os
import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

# ── Configuration ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = os.environ.get("BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = "client_tickets"
DELAY_BETWEEN_MESSAGES = 1  # secondes entre chaque ticket

# ── Données de simulation ──────────────────────────────────────────────────────
REQUEST_TYPES = [
    "Facturation",
    "Support technique",
    "Retour produit",
    "Livraison",
    "Information",
]

REQUESTS = {
    "Facturation": [
        "Je n'ai pas reçu ma facture du mois dernier.",
        "Il y a une erreur sur mon dernier relevé.",
        "Je voudrais changer mon mode de paiement.",
    ],
    "Support technique": [
        "Mon application ne se lance plus depuis ce matin.",
        "Je n'arrive pas à me connecter à mon compte.",
        "Le module de reporting est inaccessible.",
    ],
    "Retour produit": [
        "Je souhaite retourner un article défectueux.",
        "Le produit reçu ne correspond pas à ma commande.",
        "Je veux échanger mon produit contre un autre modèle.",
    ],
    "Livraison": [
        "Ma commande n'est pas arrivée dans les délais prévus.",
        "Mon colis semble perdu, aucune mise à jour depuis 5 jours.",
        "L'adresse de livraison est incorrecte sur ma commande.",
    ],
    "Information": [
        "Quelles sont vos heures d'ouverture ?",
        "Pouvez-vous me donner des informations sur vos offres ?",
        "Comment puis-je mettre à jour mon profil ?",
    ],
}

PRIORITIES = ["low", "medium", "high", "critical"]


# ── Générateur de ticket ───────────────────────────────────────────────────────
def generate_ticket(ticket_id: int) -> dict:
    request_type = random.choice(REQUEST_TYPES)
    return {
        "ticket_id": f"TKT-{ticket_id:05d}",
        "client_id": f"CLT-{random.randint(1000, 9999)}",
        "created_at": datetime.now().isoformat(),
        "request_type": request_type,
        "request": random.choice(REQUESTS[request_type]),
        "priority": random.choice(PRIORITIES),
    }


# ── Producteur Kafka ───────────────────────────────────────────────────────────
def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    print(f"✅ Connecté à Redpanda ({BOOTSTRAP_SERVERS})")
    print(f"📤 Envoi des tickets vers le topic '{TOPIC}'...\n")

    ticket_id = 1
    try:
        while True:
            ticket = generate_ticket(ticket_id)

            # On utilise le client_id comme clé pour garantir
            # que les tickets d'un même client vont dans la même partition
            producer.send(
                topic=TOPIC,
                key=ticket["client_id"],
                value=ticket,
            )

            print(f"[{ticket['created_at']}] Ticket envoyé : {ticket['ticket_id']} "
                  f"| Client : {ticket['client_id']} "
                  f"| Type : {ticket['request_type']} "
                  f"| Priorité : {ticket['priority']}")

            ticket_id += 1
            time.sleep(DELAY_BETWEEN_MESSAGES)

    except KeyboardInterrupt:
        print("\n⛔ Arrêt du producteur.")
    finally:
        producer.flush()
        producer.close()
        print("✅ Producteur fermé proprement.")


if __name__ == "__main__":
    main()