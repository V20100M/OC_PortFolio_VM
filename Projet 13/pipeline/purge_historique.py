"""
pipeline/purge_historique.py
------------------------------
Purge automatique de l'historique conversationnel de plus de 2 mois
(minimisation des donnees, conformite RGPD).
"""

from backend.database import get_connection


def purge_historique(jours=60):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM historiques_chatbot WHERE date_echange < now() - (%s || ' days')::interval",
                    (jours,),
                )
                lignes_supprimees = cur.rowcount
    finally:
        conn.close()

    print(f"{lignes_supprimees} lignes supprimees de historiques_chatbot (plus de {jours} jours).")
    return lignes_supprimees


if __name__ == "__main__":
    purge_historique()