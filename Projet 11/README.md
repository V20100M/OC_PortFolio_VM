# Puls-Events — POC Système RAG

Proof of Concept d'un chatbot basé sur un système de génération augmentée par récupération (RAG), capable de recommander des événements culturels en Gironde à partir des données Open Agenda.

---

## Prérequis

- Python 3.10 ou supérieur
- Une clé API Mistral (https://console.mistral.ai)
- Une clé API Open Agenda (https://openagenda.com)

---

## Installation

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd pulsevents
```

### 2. Créer et activer l'environnement virtuel

**Windows (PowerShell) :**
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

**Windows (Git Bash) :**
```bash
python -m venv .venv
source .venv/Scripts/activate
```

**Linux / macOS :**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créer un fichier `.env` à la racine du projet :

```
MISTRAL_API_KEY=votre_clé_mistral
OPEN_AGENDA_KEY=votre_clé_open_agenda
```

---

## Structure du projet

```
pulsevents/
│
├── config.py                       # Configuration centralisée (clés API, chemins, paramètres)
│
├── data/
│   ├── events.csv                  # Événements nettoyés
│   ├── events.json                 # Événements au format JSON
│   ├── events_sans_ville.csv       # Événements sans ville écartés (généré si nécessaire)
│   ├── embeddings.npy              # Vecteurs générés par mistral-embed
│   ├── faiss_index.bin             # Index vectoriel FAISS
│   ├── faiss_metadatas.json        # Métadonnées associées aux chunks
│   ├── test_dataset.json           # Jeu de données test annoté
│   ├── evaluation_report.json      # Rapport d'évaluation généré
│   └── feedback.json               # Retours utilisateurs sur les réponses du chatbot
│
├── scripts/
│   ├── __init__.py
│   ├── fetch_events.py             # Récupération et nettoyage des données Open Agenda
│   └── vectorize.py                # Découpage en chunks, vectorisation et indexation FAISS
│
├── tests/
│   ├── test_fetch_events.py        # Tests unitaires sur les données récupérées
│   └── test_vectorize.py           # Tests unitaires sur l'index FAISS
│
├── evaluation/
│   ├── __init__.py
│   ├── generate_test_dataset.py    # Génération du jeu de données test questions/réponses
│   └── evaluate.py                 # Évaluation automatique des réponses du chatbot
│
├── app.py                          # Interface web Streamlit du chatbot
├── chatbot.py                      # Interface chatbot RAG en ligne de commande
│
├── pyproject.toml                  # Configuration pytest
├── .env                            # Variables d'environnement (non versionné)
├── .gitignore
└── requirements.txt
```

---

## Description des fichiers

### `config.py`
Centralise toutes les constantes du projet : clés API, URLs, modèles Mistral, filtres géographiques et temporels, paramètres de vectorisation, chemins des fichiers. Toute modification de configuration doit se faire ici.
Sert également pour les tests.

### `scripts/fetch_events.py`
Récupère les événements culturels depuis l'API Open Agenda (opendatasoft), filtrés par département (Gironde par défaut) et par période (entre la date du jour et un an plus tard). Nettoie les données et les sauvegarde dans `data/events.csv` et `data/events.json`.
Écarte également les événements sans ville et les sauvegarde dans data/events_sans_ville.csv pour analyse.

### `scripts/vectorize.py`
Charge les événements depuis `data/events.csv`, construit un texte par événement, le découpe en chunks avec `RecursiveCharacterTextSplitter`, vectorise chaque chunk avec `mistral-embed`, et indexe les vecteurs dans une base FAISS. Sauvegarde l'index dans `data/faiss_index.bin` et les métadonnées dans `data/faiss_metadatas.json`.

### `chatbot.py`
Interface en ligne de commande du chatbot RAG. Charge l'index FAISS, vectorise la question de l'utilisateur, récupère les chunks les plus pertinents, construit un contexte et génère une réponse avec `mistral-small-latest` via LangChain.

### `app.py`
Interface web du chatbot RAG basée sur Streamlit. Permet à l'utilisateur de poser des questions via un navigateur et de donner un retour (👍/👎) sur chaque réponse. Les retours sont sauvegardés dans `data/feedback.json`.

### `tests/test_fetch_events.py`
Vérifie que les données récupérées respectent les contraintes du projet : présence des colonnes, absence de doublons, filtre géographique (Gironde), filtre temporel (entre la date du jour et un an plus tard), dates valides.

### `tests/test_vectorize.py`
Vérifie que l'index FAISS est cohérent : nombre de vecteurs, présence des métadonnées, champs obligatoires, et pertinence des résultats de recherche sémantique.

### `evaluation/generate_test_dataset.py`
Génère automatiquement un jeu de données test de questions/réponses en interrogeant le chatbot. Le champ `reponse_annotee` doit ensuite être rempli manuellement pour chaque entrée.

### `evaluation/evaluate.py`
Évalue automatiquement la qualité des réponses du chatbot en comparant `reponse_generee` et `reponse_annotee` à l'aide de `mistral-small-latest` comme juge. Génère un rapport d'évaluation dans `data/evaluation_report.json`.

---

## Utilisation

### Étape 1 — Récupérer les événements

```bash
python -m scripts.fetch_events
```

**Résultat attendu :**
```
Filtre : location_department='Gironde' AND lastdate_end >= '2026-05-14T...' AND lastdate_end <= '2027-05-14T...'
Récupération en cours...
Total d'événements trouvés : 2036
Récupération terminée. Total d'événements récupérés : 2036
1 événement sans ville trouvé. Sauvegarde dans 'data/events_sans_ville.csv' pour analyse.
--- Après nettoyage ---
Lignes : 2035
Fichiers sauvegardés : data/events.csv et data/events.json
Jeu de données final : 2035 événements prêts à être indexés
```

### Étape 2 — Construire la base vectorielle

```bash
python -m scripts.vectorize
```

> ⚠️ Cette étape appelle l'API `mistral-embed` et peut prendre plusieurs minutes.
> Si `data/embeddings.npy` existe déjà, les embeddings sont rechargés sans appel API.

**Résultat attendu :**
```
Événements chargés : 2035
Chunks créés : 6773
Vectorisation terminée : 6773 vecteurs générés.
Embeddings sauvegardés dans data/embeddings.npy
Index Faiss créé avec 6773 vecteurs et dimension 1024.
Index et métadonnées sauvegardés : faiss_index.bin et faiss_metadatas.json
Processus de vectorisation et d'indexation terminé avec succès.
```

### Étape 3 — Lancer le chatbot

**Option A — Interface web (recommandée) :**
```bash
streamlit run app.py
```
L'interface s'ouvre automatiquement dans le navigateur.

**Option B — Ligne de commande :**
```bash
python chatbot.py
```

**Résultat attendu :**
```
Chargement du chatbot...
Index chargé avec 6773 vecteurs
Métadonnées chargées : 6773 chunks
Chatbot Puls-Events prêt à répondre à vos questions sur les événements culturels en Gironde !
Posez vos questions sur les événements en Gironde (ou tapez 'quitter' pour quitter) :
Vous :
```

**Exemples de questions :**
```
Vous : Quels concerts sont prévus à Bordeaux ?
Vous : Y a-t-il des expositions à Mérignac ?
Vous : Quels événements pour les enfants ce mois-ci ?
Vous : Y a-t-il des événements concernant les jeux vidéo en Gironde ?
```

---

## Tests

### Lancer tous les tests

```bash
pytest tests/ -v
```

**Résultat attendu :**
```
collected 15 items

tests/test_fetch_events.py::test_fichier_non_vide PASSED
tests/test_fetch_events.py::test_colonnes_presentes PASSED
tests/test_fetch_events.py::test_pas_de_titre_manquant PASSED
tests/test_fetch_events.py::test_pas_de_description_manquante PASSED
tests/test_fetch_events.py::test_pas_de_ville_manquante PASSED
tests/test_fetch_events.py::test_pas_de_doublons PASSED
tests/test_fetch_events.py::test_filtre_geographique PASSED
tests/test_fetch_events.py::test_filtre_temporel PASSED
tests/test_fetch_events.py::test_dates_valides PASSED
tests/test_vectorize.py::test_index_non_vide PASSED
tests/test_vectorize.py::test_metadatas_non_vides PASSED
tests/test_vectorize.py::test_aucun_chunk_vide PASSED
tests/test_vectorize.py::test_coherence_index_metadatas PASSED
tests/test_vectorize.py::test_metadatas_champs_requis PASSED
tests/test_vectorize.py::test_pertinence_recherche PASSED

15 passed in 1.93s
```

### Lancer un fichier de tests spécifique

```bash
pytest tests/test_fetch_events.py -v
pytest tests/test_vectorize.py -v
```

---

## Évaluation

### Générer le jeu de données test

```bash
python -m evaluation.generate_test_dataset
```

> ⚠️ Ne relance pas ce script si `data/test_dataset.json` existe déjà — cela ne l'écrasera pas.
> Supprime-le manuellement si tu souhaites le régénérer.

Remplis ensuite manuellement le champ `reponse_annotee` dans `data/test_dataset.json` pour chaque entrée.

### Lancer l'évaluation

```bash
python -m evaluation.evaluate
```

**Résultat attendu :**
```
Jeu de données chargé : 12 questions
Évaluation des 12 questions/réponses.

  Question 1 : Incorrecte - ...
  Question 2 : Correcte - ...
  ...

Résultats de l'évaluation : 10 réponses correctes sur 12 évaluées.
Précision globale : 83.33%
Rapport d'évaluation sauvegardé : data/evaluation_report.json
```


---

## Modifier la zone géographique

Pour changer la zone géographique des événements, modifier dans `config.py` :

```python
GEO_FILTER_FIELD = "location_department"   # ou "location_city" ou "location_region"
GEO_FILTER_VALUE = "Gironde"               # ex: "Bordeaux", "Nouvelle-Aquitaine"
```

Puis relancer les étapes 1 et 2 pour reconstruire la base de données.

---

## Remarques

- Le dossier `data/` n'est pas versionné (ajouté au `.gitignore`). Il doit être reconstruit en suivant les étapes ci-dessus.
- Le fichier `.env` ne doit jamais être versionné.
- La base vectorielle peut être reconstruite à tout moment en supprimant `data/embeddings.npy` et en relançant `python -m scripts.vectorize`. Les événements récupérés couvrent la période entre la date du jour et un an plus tard.
- Si des événements sans ville sont détectés lors du nettoyage, ils sont sauvegardés dans data/events_sans_ville.csv pour analyse.
- Les retours utilisateurs (👍/👎) sont sauvegardés dans data/feedback.json et peuvent être utilisés pour améliorer le système.
