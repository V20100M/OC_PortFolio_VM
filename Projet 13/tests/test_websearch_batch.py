"""
test_websearch_batch.py
--------------------------
Test de faisabilite sur plusieurs questions variees, pour mesurer
latence et consommation de credits Tavily de facon plus fiable qu'avec
1-2 questions isolees.
"""

import time
from websearch_agent import get_websearch_response

QUESTIONS = [
    ("Y a-t-il des concerts ce week-end ?", "Bordeaux"),
    ("Quels evenements sportifs cette semaine ?", "Lyon"),
    ("Y a-t-il des expositions en ce moment ?", "Paris"),
    ("Quels festivals ce mois-ci ?", "Toulouse"),
    ("Y a-t-il des marches de noel ?", "Strasbourg"),
    # Cas volontairement improbable, pour observer un vrai "rien trouve"
    ("Y a-t-il un concert de heavy metal mongol traditionnel demain ?", "Mérignac"),
]

if __name__ == "__main__":
    resultats = []
    for question, ville in QUESTIONS:
        print(f"\n=== {ville} : {question} ===")
        debut = time.time()
        try:
            reponse = get_websearch_response(question, ville)
            duree = time.time() - debut
            print(f"Duree : {duree:.1f}s")
            print(f"Reponse : {reponse[:300]}...")
            resultats.append((ville, question, duree, "OK"))
        except Exception as e:
            duree = time.time() - debut
            print(f"ECHEC apres {duree:.1f}s : {e}")
            resultats.append((ville, question, duree, f"ECHEC: {e}"))

    print("\n\n=== RECAPITULATIF ===")
    for ville, question, duree, statut in resultats:
        print(f"{ville:15} | {duree:6.1f}s | {statut[:50]}")