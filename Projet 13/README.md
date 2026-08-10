# Puls-Events — Chatbot RAG d'événements culturels

Puls-Events est un chatbot basé sur un système de génération augmentée par récupération (RAG) qui recommande des événements culturels en France à partir des données [Open Agenda](https://openagenda.com). Le projet est passé d'un POC Streamlit à une architecture multi-services conteneurisée : API FastAPI, base PostgreSQL, pipeline de données bronze/gold orchestré par Kestra, recherche vectorielle Qdrant, agent de recherche web de secours, et observabilité PostgreSQL via Grafana Cloud.

---

## Architecture

```
Open Agenda (opendatasoft)
        │
        ▼
┌───────────────────────────── Pipeline (pipeline/) ─────────────────────────────┐
│ fetch_last_events → load_bronze → transform_gold → load_gold → send_gold_to_qdrant │
└───────────────────────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
  PostgreSQL (bronze/gold,        Qdrant (index vectoriel
  utilisateurs, historiques,      des événements, filtres géo)
  interactions_log)                       │
        ▲                                 │
        │                                 ▼
        │                        FastAPI backend (backend/)
        │                        /auth, /chat, /feedback, /health
        │                        RAG (LangChain + Mistral) avec
        │                        repli websearch_agent (Tavily)
        │                                 │
        └─────────────────────────────────┤
                                           ▼
                          Streamlit (app.py)  +  site web / widget (web/)

Orchestration : Kestra (kestra/flows/) — planifie le pipeline quotidien et
                la purge RGPD de l'historique.
Observabilité : Grafana Alloy (alloy/) — envoie métriques et logs Postgres
                vers Grafana Cloud via un agent PDC.
```

**Flux de données :**
1. `pipeline/fetch_last_events.py` récupère les événements Open Agenda (France entière, incrémental sur `updatedat`) → `data/pipeline/bronze_input.json`.
2. `pipeline/load_bronze.py` charge le JSON brut dans la table `evenements_bronze` (Postgres), avec déduplication.
3. `pipeline/transform_gold.py` nettoie les lignes non traitées (titre/description/ville manquants écartés) → `data/pipeline/gold_input.json`.
4. `pipeline/load_gold.py` upsert les événements nettoyés dans `evenements_gold` et marque les lignes bronze comme traitées.
5. `pipeline/send_gold_to_qdrant.py` découpe en chunks, vectorise avec `mistral-embed` et indexe dans Qdrant (collection `evenements`) avec métadonnées géographiques (ville/département/région).
6. Les étapes 1 à 5 sont orchestrées chaque jour à 6h par Kestra (`kestra/flows/pipeline-evenements-quotidien.yml`) ; une variante manuelle (`pipeline-evenements-initial.yml`) sert au backfill initial. Un flow séparé (`purge-historique.yml`) purge quotidiennement l'historique de conversation de plus de 60 jours (RGPD).
7. Le backend FastAPI (`backend/`) expose l'authentification (JWT + bcrypt), le chat (recherche RAG filtrée par géolocalisation dans Qdrant via LangChain + Mistral, avec repli sur `websearch_agent.py`/Tavily si aucun résultat pertinent) et le feedback utilisateur. Chaque échange est journalisé dans `historiques_chatbot` et `interactions_log`.
8. Deux frontends consomment l'API : l'app Streamlit (`app.py`, géolocalisation IP navigateur ou recherche manuelle de ville) et un site statique + widget de chat embarquable (`web/`, servi par nginx).
9. Grafana Alloy (`alloy/config.alloy`) collecte les métriques et logs PostgreSQL (`pg_stat_statements`) et les envoie à Grafana Cloud via un agent Private Datasource Connect (`pdc-agent`).

---

## Stack technique

- **API** : FastAPI, uvicorn
- **RAG / LLM** : LangChain, Mistral AI (`mistral-embed`, `mistral-small-latest`) via `langchain-mistralai` et le SDK `mistralai`
- **Recherche vectorielle** : Qdrant (production) ; FAISS (`faiss-cpu`, workflow historique conservé dans `scripts/`)
- **Agent web de secours** : smolagents (`ToolCallingAgent`) + LiteLLM + Tavily
- **Base de données** : PostgreSQL 18 (`psycopg2-binary`)
- **Frontends** : Streamlit, site statique HTML/CSS/JS + widget de chat (nginx)
- **Authentification** : bcrypt, PyJWT
- **Orchestration** : Kestra (flows Docker planifiés par cron)
- **Observabilité** : Grafana Alloy, Grafana Cloud (métriques + logs), PDC agent
- **Conteneurisation** : Docker, docker-compose

---

## Prérequis

- Docker et Docker Compose
- Une clé API [Mistral](https://console.mistral.ai)
- Une clé API [Open Agenda](https://openagenda.com)
- Une clé API [Tavily](https://tavily.com) (pour le repli de recherche web)
- (Optionnel) Un compte Grafana Cloud si vous souhaitez activer l'observabilité (`alloy` / `pdc-agent`)

---

## Installation et lancement (Docker Compose — recommandé)

### 1. Cloner le dépôt

```bash
git clone https://github.com/V20100M/OC_PortFolio_VM.git
cd "Projet 13"
```

### 2. Configurer les variables d'environnement

Créer un fichier `.env` à la racine du projet avec les variables suivantes :

```
# APIs externes
MISTRAL_API_KEY=
OPEN_AGENDA_KEY=
TAVILY_API_KEY=

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Backend
API_BASE_URL=http://backend:8000
JWT_SDK_SECRET_KEY=

# Secrets Kestra (dupliquent les valeurs ci-dessus pour le secret store des flows)
SECRET_MISTRAL_API_KEY=
SECRET_OPEN_AGENDA_KEY=
SECRET_POSTGRES_PASSWORD=

# Observabilité Grafana Cloud (optionnel)
PDC_TOKEN=
DB_O11Y_DSN=
GCLOUD_HOSTED_METRICS_URL=
GCLOUD_HOSTED_METRICS_ID=
GCLOUD_HOSTED_LOGS_URL=
GCLOUD_HOSTED_LOGS_ID=
GCLOUD_RW_API_KEY=
```

### 3. Lancer l'ensemble des services

```bash
docker compose up -d --build
```

Services démarrés :

| Service      | Rôle                                              | Port hôte |
|--------------|----------------------------------------------------|-----------|
| `postgres`   | Base de données (app + Kestra)                     | 5433      |
| `backend`    | API FastAPI (`/auth`, `/chat`, `/feedback`, `/health`) | 8000      |
| `streamlit`  | Interface web du chatbot                            | 8501      |
| `web`        | Site statique + widget de chat embarquable (nginx)  | 8080      |
| `qdrant`     | Base vectorielle                                    | 6333      |
| `kestra`     | Orchestrateur de workflows                          | 8081      |
| `pdc-agent`  | Tunnel Grafana Private Datasource Connect           | —         |
| `alloy`      | Collecte métriques/logs Postgres → Grafana Cloud    | 12345     |

### 4. Charger les données initiales

Le premier chargement des événements se fait via le flow Kestra dédié :

1. Ouvrir l'interface Kestra sur [http://localhost:8081](http://localhost:8081).
2. Déclencher manuellement le flow `pulsevents.pipeline-evenements-initial` (namespace `pulsevents`) pour le backfill initial (jusqu'à 730 jours d'événements).
3. Le flow quotidien `pulsevents.pipeline-evenements-quotidien` (cron `0 6 * * *`) prend ensuite le relais automatiquement pour les mises à jour incrémentales.
4. Le flow `pulsevents.purge-historique` (cron `0 3 * * *`) purge chaque jour l'historique de conversation de plus de 60 jours.

### 5. Utiliser le chatbot

- Interface web Streamlit : [http://localhost:8501](http://localhost:8501)
- Site + widget embarquable : [http://localhost:8080](http://localhost:8080)
- API directe : [http://localhost:8000/docs](http://localhost:8000/docs) (documentation Swagger FastAPI)

---

## Structure du projet

```
pulsevents/
│
├── app.py                     # Interface Streamlit (client HTTP de l'API backend)
├── chatbot.py                 # Construction de la chaîne RAG LangChain + Mistral (utilisé par le backend et le CLI legacy)
├── chatbot_qdrant.py          # Recherche sémantique Qdrant avec filtrage géographique
├── geolocation.py             # Géolocalisation IP navigateur + recherche de commune (geo.api.gouv.fr)
├── websearch_agent.py         # Agent de recherche web de secours (smolagents + Tavily)
├── vectorize_qdrant.py        # Script d'essai de vectorisation vers Qdrant
├── config.py                  # Configuration centralisée (clés API, chemins, paramètres)
│
├── backend/                   # API FastAPI
│   ├── main.py                 # Point d'entrée, montage des routers, /health
│   ├── database.py             # Connexion PostgreSQL (psycopg2)
│   ├── schemas.py               # Modèles Pydantic
│   ├── security.py              # Hash bcrypt + JWT
│   └── routers/
│       ├── auth.py              # POST /auth/register, /auth/login
│       └── chat.py              # POST /chat, POST /feedback
│
├── pipeline/                  # Pipeline de données bronze/gold
│   ├── fetch_last_events.py    # Ingestion incrémentale Open Agenda (France entière)
│   ├── load_bronze.py           # Chargement JSON brut → evenements_bronze
│   ├── transform_gold.py        # Nettoyage bronze → gold
│   ├── load_gold.py             # Upsert evenements_gold
│   ├── send_gold_to_qdrant.py   # Vectorisation + indexation Qdrant
│   └── purge_historique.py      # Purge RGPD de historiques_chatbot (> 60 jours)
│
├── kestra/flows/               # Orchestration Kestra (YAML)
│   ├── pipeline-evenements-quotidien.yml  # Pipeline complet, cron quotidien
│   ├── pipeline-evenements-initial.yml    # Pipeline complet, déclenchement manuel (backfill)
│   └── purge-historique.yml               # Purge RGPD, cron quotidien
│
├── alloy/
│   └── config.alloy            # Config Grafana Alloy (métriques/logs Postgres → Grafana Cloud)
│
├── sql/
│   ├── database.sql, roles.sql, truncate_all.sql   # Scripts SQL manuels/legacy
│   └── init/                   # Scripts d'initialisation auto-exécutés par le conteneur Postgres
│       ├── 01_roles.sql                 # Rôle applicatif
│       ├── 02_create_tables.sql         # utilisateurs, identifiants, historiques_chatbot
│       ├── 03_pipeline_tables.sql       # evenements_bronze, evenements_gold
│       ├── 04_kestra_database.sql       # Base dédiée à Kestra
│       ├── 05_interactions_log.sql      # interactions_log (feedback, latence, source)
│       ├── 06_grafana_reader.sql        # Rôle lecture seule pour Grafana
│       └── 07_database_observability.sql # Rôle db-o11y + pg_stat_statements
│
├── scripts/                   # Pipeline legacy (FAISS, mono-zone géographique)
│   ├── fetch_events.py
│   └── vectorize.py
│
├── utils/
│   └── logging_utils.py        # Configuration de logs partagée (backend + scripts)
│
├── web/                        # Site statique + widget de chat (nginx)
│   ├── index.html, script.js, style.css
│   ├── widget.js, widget.css
│   └── Dockerfile
│
├── tests/
│   └── test_websearch_batch.py # Benchmark manuel de l'agent de recherche web
│
├── data/                       # Données locales/intermédiaires (non versionné)
├── logs/                       # Logs applicatifs (non versionné)
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── .env                        # Variables d'environnement (non versionné)
```

---

## API — principaux endpoints

| Méthode | Route             | Description                                                        |
|---------|--------------------|----------------------------------------------------------------------|
| POST    | `/auth/register`  | Crée un utilisateur (email + mot de passe hashé bcrypt), renvoie un JWT |
| POST    | `/auth/login`      | Authentifie un utilisateur, renvoie un JWT                          |
| POST    | `/chat`            | Pose une question ; recherche RAG dans Qdrant filtrée par géo, repli sur recherche web si aucun résultat pertinent ; journalise l'échange |
| POST    | `/feedback`        | Enregistre un retour 👍/👎 sur une réponse (`interactions_log`)      |
| GET     | `/health`          | Vérification de disponibilité                                       |

---

## Développement local sans Docker (composants Python isolés)

Pour travailler sur un script individuel sans lancer toute la stack :

```bash
python -m venv .venv
.\.venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
```

Un PostgreSQL et un Qdrant accessibles (locaux ou via `docker compose up postgres qdrant`) restent nécessaires pour la plupart des scripts (`backend/`, `pipeline/`). Le workflow historique 100 % local (FAISS, sans backend) reste disponible :

```bash
python -m scripts.fetch_events     # Récupère et nettoie les événements (zone définie dans config.py)
python -m scripts.vectorize        # Vectorise et indexe dans FAISS
python chatbot.py                  # Chatbot RAG en ligne de commande (FAISS local)
```

---

## Tests

```bash
pytest tests/ -v
```

> `tests/test_websearch_batch.py` est un script de benchmark manuel de latence/pertinence pour l'agent de recherche web (Tavily), pas une suite d'assertions automatisées.

---

## Observabilité

Grafana Alloy (`alloy/config.alloy`) scrape les statistiques PostgreSQL (`pg_stat_statements`, plugin `database_observability.postgres`) et transmet métriques et logs à Grafana Cloud via `prometheus.remote_write` et `loki.write`, en s'appuyant sur le tunnel `pdc-agent` (Grafana Private Datasource Connect). Nécessite les variables `DB_O11Y_DSN`, `GCLOUD_HOSTED_METRICS_*`, `GCLOUD_HOSTED_LOGS_*`, `GCLOUD_RW_API_KEY` et `PDC_TOKEN`.

---

## Remarques

- Les dossiers `data/` et `logs/` ne sont pas versionnés ; `data/pipeline/` est régénéré par le pipeline (`fetch_last_events.py` → `bronze_input.json`, `transform_gold.py` → `gold_input.json`).
- Le fichier `.env` ne doit jamais être versionné.
- Kestra pousse ses tâches de pipeline dans des conteneurs Docker (`pulsevents-backend:latest`, construit depuis le `Dockerfile` racine) via `/var/run/docker.sock` monté dans le conteneur `kestra` — reconstruire l'image (`docker compose build backend`) avant de relancer un flow après modification du code du pipeline.
- La zone géographique n'est plus limitée à la Gironde : le pipeline `pipeline/` ingère les événements de la France entière et le filtrage géographique se fait à la requête, côté Qdrant, à partir de la géolocalisation de l'utilisateur.
