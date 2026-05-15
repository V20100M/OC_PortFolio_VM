import json
import os
from mistralai.client import Mistral
from config import MISTRAL_API_KEY, LLM_MODEL, TEST_DATASET_JSON, EVALUATION_REPORT_JSON


def load_dataset():
    if not os.path.exists(TEST_DATASET_JSON):
        print(f"Le fichier {TEST_DATASET_JSON} n'existe pas. Veuillez d'abord générer le jeu de données avec 'generate_test_dataset.py'.")
        return None
    with open(TEST_DATASET_JSON, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    print(f"Jeu de données chargé : {len(dataset)} questions")
    return dataset


def evaluate_response(client, question, reponse_generee, reponse_annotee):
    prompt = f"""Tu es un évaluateur impartial de systèmes de recommandation d'événements culturels.
    Ta tâche est de comparer la réponse générée par un chatbot à une réponse annotée de référence, et d'évaluer la qualité de la réponse
    générée en fonction de plusieurs critères. Voici les éléments à prendre en compte pour ton évaluation :

    Une réponse est considérée comme correcte si elle contient des informations pertinentes et cohérentes avec la question, même si elle ne
    mentionne pas exactement les mêmes événements que la réponse de référence.
    Une réponse est considérée comme incorrecte si elle est hors sujet, contient des informations erronées, ou ne répond pas à la question.


    Question : {question}

    Réponse générée par le chatbot : {reponse_generee}

    Réponse annotée (référence) : {reponse_annotee}


    Réponds uniquement en JSON avec ce format :
    {{
        "correct": true ou false,
        "justification": "Une explication courte de ton évaluation en français, mettant en évidence les points forts et les points faibles
        de la réponse générée par rapport à la réponse annotée."
    }}
    """

    response = client.chat.complete(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    evaluation = response.choices[0].message.content.strip()
    # Nettoyage de la réponse pour s'assurer qu'elle est un JSON valide
    evaluation = evaluation.replace("```json", "").replace("```", "").strip()
    return json.loads(evaluation)


def evaluate():
    client = Mistral(api_key=MISTRAL_API_KEY)
    dataset = load_dataset()

    if dataset is None:
        print("Aucun jeu de données à évaluer. Terminaison du processus.")
        return

    results = []
    correct_count = 0

    print(f"Évaluation des {len(dataset)} questions/réponses.\n")

    for entry in dataset:
        if not entry.get("reponse_annotee"):
            print(f"  Question {entry['id']} : Pas de réponse annotée, évaluation ignorée.")
            continue

        result = evaluate_response(
            client,
            entry["question"],
            entry["reponse_generee"],
            entry["reponse_annotee"]
        )

        status = "Correcte" if result["correct"] else "Incorrecte"
        print(f"  Question {entry['id']} : {status} - {result['justification']}")

        results.append({
            "id": entry["id"],
            "question": entry["question"],
            "correct": result["correct"],
            "justification": result["justification"]
        })

        if result["correct"]:
            correct_count += 1

    total_evaluated = len(results)
    accuracy = correct_count / total_evaluated * 100 if total_evaluated > 0 else 0

    print(f"\nRésultats de l'évaluation : {correct_count} réponses correctes sur {total_evaluated} évaluées.")
    print(f"Précision globale : {accuracy:.2f}%")

    report = {
        "précision": f"{correct_count}/{total_evaluated}",
        "pourcentage": f"{accuracy:.2f}%",
        "resultats": results
    }

    os.makedirs("data", exist_ok=True)
    with open(EVALUATION_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Rapport d'évaluation sauvegardé : {EVALUATION_REPORT_JSON}")


if __name__ == "__main__":
    evaluate()