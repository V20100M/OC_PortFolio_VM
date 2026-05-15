import json
import os

from chatbot import load_index, build_rag_chatbot, get_chatbot_response
from config import TEST_DATASET_JSON

# ============================================================
# QUESTIONS DE TEST
# ============================================================
QUESTIONS = [
    "Quels concerts sont prévus à Bordeaux ?",
    "Y a-t-il des expositions d'art en Gironde ?",
    "Quels événements pour les enfants sont disponibles ?",
    "Y a-t-il des spectacles de danse en Gironde ?",
    "Quels événements sportifs sont prévus en Gironde ?",
    "Quels événements ont lieu à Mérignac ?",
    "Y a-t-il des événements à Pessac ?",
    "Y a-t-il des événements autour du cinéma en Gironde ?",
    "Quels événements concernent la gastronomie ou le vin ?",
    "Y a-t-il des conférences ou débats en Gironde ?",
    "Y a-t-il des événements liés à la nature ou l'environnement ?",
    "Y a-t-il des événements concernant les jeux vidéo en Gironde ?"
]

# ============================================================
# GÉNÉRATION DU JEU DE DONNÉES
# ============================================================
def generate_test_dataset():
    print("Chargement du chatbot...")
    index, metadatas = load_index()
    chain = build_rag_chatbot()

    dataset = []

    for i, question in enumerate(QUESTIONS):
        print(f"  Génération {i+1}/{len(QUESTIONS)} : {question}")

        response = get_chatbot_response(index, metadatas, question, chain)

        dataset.append({
            "id": i + 1,
            "question": question,
            "reponse_generee": response,
            "reponse_annotee": ""  # À remplir manuellement
        })

    return dataset

# ============================================================
# SAUVEGARDE
# ============================================================
def save_dataset(dataset):
    os.makedirs("data", exist_ok=True)
    if os.path.exists(TEST_DATASET_JSON):
        print(f"Le fichier {TEST_DATASET_JSON} existe déjà.")
        print("Pour éviter d'écraser les réponses annotées, le fichier n'a pas été modifié.")
        print("Supprimez-le manuellement si vous souhaitez le régénérer.")
        return
    with open(TEST_DATASET_JSON, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"\nJeu de données sauvegardé : {TEST_DATASET_JSON}")
    print(f"Prochaine étape : remplir le champ 'reponse_annotee' pour chaque entrée.")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    dataset = generate_test_dataset()
    save_dataset(dataset)