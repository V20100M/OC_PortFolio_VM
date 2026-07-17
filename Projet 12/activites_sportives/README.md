# POC — Gestion des avantages sportifs

Pipeline de données complet pour gérer les activités sportives des salariés et calculer leur éligibilité aux primes sport, avec capture de changements en temps réel et notifications Slack.

---

## Architecture globale

```
Données Excel (RH + Sport)
        ↓
  [analyse_rh.py]
  (visualisation)
        ↓
  [import_excel.py]
        ↓
  PostgreSQL ─────────────────────────────────────┐
        ↓                                          │
  [geocode_adresses.py]                    Debezium CDC
  (Nominatim + OSRM)                              │
        ↓                                          ↓
  [data_quality_check.py]              Redpanda (Kafka)
  (Great Expectations — passe 1)                  │
        ↓                                          ↓
  [generate_strava_raw.py]              [consumer_slack.py]
  (bronze → strava_raw)                             │
        ↓                                          ↓
  [etl_strava.py]                          Slack webhook
  (gold → strava + stravathlete
   + strava_comment)
        ↓
  [data_quality_check.py]
  (Great Expectations — passe 2 + strava)
```

### Flux temps réel — `pipeline_live.py`

```
[simulate_strava_activity.py]     bronze : dépose un JSON dans strava_raw
        ↓                                  (+ strava_comment_raw)
  [etl_strava.py]                  gold   : transforme et insère dans strava
        ↓                                  → déclenche Debezium CDC
  PostgreSQL (WAL) → Debezium → Redpanda → consumer_slack.py → Slack webhook
```

### Flux temps réel — `pipeline_live.py`

```
[import_excel.py]          upsert des données RH depuis Données+RH.xlsx
        ↓
[geocode_adresses.py]      regéocodage des adresses modifiées uniquement
        ↓
[data_quality_check.py]    validation qualité post-mise à jour
```


### Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.11+ |
| Base de données | PostgreSQL 17 (logical replication) |
| Message broker | Redpanda (Kafka-compatible) |
| CDC | Debezium 2.7 |
| Orchestration | Kestra |
| Géocodage | Nominatim (OSM) + OSRM |
| Qualité des données | Great Expectations 1.18.1 |
| Tests unitaires | pytest |
| Notifications | Slack webhooks |
| Conteneurisation | Docker Compose |

---

## Structure du projet

```
activites_sportives/
├── .env                          # Variables d'environnement (DB, Slack, Kafka)
├── requirements.txt              # Dépendances Python
├── Dockerfile                    # Image Python pour le conteneur pipeline
├── docker-compose.yml            # Orchestration de tous les services
├── run_pipeline.py               # Orchestrateur principal (7 étapes séquentielles)
├── pipeline_live.py              # Orchestrateur du flux temps réel (2 étapes)
├── update_salaries.py            # Orchestrateur de mise à jour des données salariés (3 étapes)
│
├── sql/
│   ├── databases.sql             # Création des bases activitessportives + kestra
│   ├── roles.sql                 # Création du rôle sport_role et permissions
│   ├── create_tables.sql         # Schéma complet (10 tables + contraintes)
│   └── truncate_all.sql          # Vidage des tables (respecte les FK)
│
├── data/
│   ├── Données+RH.xlsx           # 161 salariés, 11 colonnes
│   └── Données+Sportive.xlsx     # 95 salariés avec sport déclaré
│
├── tests/
│   ├── conftest.py                # Config pytest (sys.path + neutralisation des logs)
│   └── test_unitaires.py          # 26 tests unitaires sur les fonctions pures
│
├── scripts/
│   ├── analyse_rh.py               # Étape 1 — visualisation des données RH
│   ├── import_excel.py             # Étape 2 — import Excel → PostgreSQL
│   ├── geocode_adresses.py         # Étape 3 — géocodage + éligibilité prime
│   ├── data_quality_check.py       # Étapes 4 et 7 — validation qualité (bloquant)
│   ├── generate_strava_raw.py      # Étape 5 — génération brute (bronze → strava_raw)
│   ├── etl_strava.py               # Étape 6 — transformation (gold → strava, live inclus)
│   ├── consumer_slack.py           # Consumer Kafka → notifications Slack
│   └── simulate_strava_activity.py # Dépôt d'une activité brute (bronze) en temps réel
│
├── utils/
│   ├── config.py                 # Constantes métier (sports, seuils, adresses)
│   ├── db.py                     # Connexion PostgreSQL partagée
│   ├── helpers.py                # Utilitaires (découverte de fichiers, filtrage sport)
│   ├── logging_utils.py          # Configuration des logs (UTF-8, console + fichier)
│   ├── strava_generation.py      # Générateur de métriques sportives partagé
│   ├── strava_etl.py             # Couche ETL partagée (simulation + parsing + insertion)
│   └── data_quality.py           # Règles Great Expectations (5 familles de validations)
│
├── flows/
│   └── notify_slack_strava.yml   # Workflow Kestra (consumer_slack toutes les 1 min)
│
├── connector-config.json         # Configuration du connecteur Debezium
└── logs/                         # Logs et visuels générés à l'exécution
    ├── analyse_rh.log / .png
    ├── import_excel.log
    ├── geocode_adresses.log
    ├── data_quality_check.log
    ├── generate_strava_raw.log
    ├── etl_strava.log
    ├── simulate_strava_activity.log
    ├── pipeline_live.log
    └── consumer_slack.log
```

---

## Schéma de la base de données

```
-- Données RH
salarie         (id_salarie PK, nom, prenom, date_naissance, bu,
                 date_embauche, salaire_brut, type_contrat,
                 jours_cp, adresse_domicile, moyen_deplacement)

sportpratique   (id_salarie PK/FK, pratique_sport)

-- Géocodage & éligibilité
salarie_geocode (id_salarie PK/FK, latitude, longitude,
                 geocode_ok, distance_km, eligible_prime)

-- Données Strava simulées
athlete         (id_athlete PK)

salarieathlete  (id_salarie PK/FK, id_athlete FK)   -- 1 salarié = 1 compte Strava

-- Couche bronze : JSON bruts au format API Strava, non transformés
strava_raw          (id PK, id_strava, raw_activity JSONB,
                     inserted_at, processed)          -- alimentée par generate_strava_raw.py
                                                        -- et simulate_strava_activity.py

strava_comment_raw  (id PK, id_strava, raw_comment JSONB,
                     inserted_at, processed)           -- idem, un enregistrement par commentaire

-- Couche gold : données transformées par etl_strava.py depuis la couche bronze
strava          (id_strava PK, start_date, end_date,
                 sport_type, distance, moving_time, elapsed_time,
                 avg_speed, max_speed, avg_watt, max_watt)

stravathlete    (id_strava PK/FK, id_athlete FK)    -- liaison activité / athlète

strava_comment  (id_comment PK, id_strava FK,
                 texte, auteur, created_at)          -- commentaires Strava (30 % de probabilité)
```

---

## Installation

### Prérequis

- Docker & Docker Compose
- Python 3.11+ (pour l'exécution locale)

### Démarrage avec Docker

```bash
# Lancer tous les services (PostgreSQL, Redpanda, Kestra, Debezium)
docker compose up -d

# Lancer le pipeline une première fois (données non présentes en base)
docker compose run --rm pipeline python run_pipeline.py

# Suivre l'exécution du pipeline
docker compose logs -f pipeline

# Arrêter tous les services
docker compose down

# Arrêter tous les services et supprimer les volumes (repart de zéro)
docker compose down -v
```

### Rebuild après modification du code

```bash
# Rebuilder l'image et redémarrer les services (données en base conservées)
docker compose up --build
```


### Exécution locale

```bash
pip install -r requirements.txt

# Copier et renseigner les variables d'environnement
cp .env.example .env

# Lancer le pipeline complet
python run_pipeline.py
```

---

## Configuration

Fichier `.env` à renseigner :

```env
# Base de données
DB_HOST=localhost
DB_PORT=5432
DB_NAME=database_name
DB_USER=database_user
DB_PASSWORD=your_password_here

# Dossier contenant les fichiers Excel
DATA_DIR=C:/chemin/vers/les/fichiers/excel

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Kafka / Redpanda
KAFKA_BOOTSTRAP_SERVERS=redpanda:9092

# Secrets encodés en base64 (pour Kestra)
SECRET_DB_PASSWORD=...
SECRET_SLACK_WEBHOOK_URL=...
```

---

## Pipeline principal — `run_pipeline.py`

Exécute **7 étapes séquentielles**. Le pipeline s'arrête à la première erreur.
Un délai de 30 secondes précède le lancement pour laisser PostgreSQL terminer son initialisation (utile au démarrage via Docker Compose).

### Étape 1 — `analyse_rh.py`

Analyse et visualise la répartition des salariés selon leur pratique sportive et leur moyen de déplacement. Génère `logs/analyse_rh.png`.

Quatre catégories colorées :
- Sport + déplacement actif (vert)
- Sport + voiture/TC (rouge)
- Pas de sport + déplacement actif (bleu)
- Pas de sport + voiture/TC (gris)

### Étape 2 — `import_excel.py`

Importe les données RH depuis les deux fichiers Excel vers PostgreSQL.

- Lit 161 salariés depuis `Données+RH.xlsx` (colonnes détectées par position)
- Lit les sports depuis `Données+Sportive.xlsx` (95 salariés concernées)
- Normalise les adresses (`Bd → Boulevard`, `Av → Avenue`, `Chem → Chemin`…)
- Gère les formats de dates : sériaux Excel, chaînes texte, bug de l'an 1900
- Upsert idempotent (`ON CONFLICT DO UPDATE`) dans `salarie` et `sportpratique`
- Valide les données via Great Expectations **avant** insertion (bloquant)
- Commit ligne par ligne : une erreur n'annule pas les lignes précédentes

### Étape 3 — `geocode_adresses.py`

Géocode les adresses domicile et calcule l'éligibilité à la prime sport.

- Géocodage via l'API Nominatim (OpenStreetMap) avec **3 stratégies de fallback** :
  1. Adresse originale + ", France"
  2. Sans le numéro de rue
  3. Avec le numéro "1" en remplacement (rues sans numéro dans OSM)
- Calcul de la distance domicile–bureau via OSRM (routage réel, profil foot ou bike)
- Rate limiting automatique : 1,1 s entre les requêtes Nominatim (bloc `finally`)

**Règles d'éligibilité :**

| Moyen de déplacement | Profil OSRM | Seuil max |
|---|---|---|
| Marche / Running | foot | 15 km |
| Vélo / Trottinette / Autres | bike | 25 km |
| Voiture / Transports en commun | — | Non éligible |

### Étape 4 — `data_quality_check.py` (passe 1)

Valide l'intégrité des données post-import via Great Expectations. **Bloque le pipeline en cas d'échec.**

| Table | Validations |
|---|---|
| `salarie` | IDs uniques, champs obligatoires (nom, prénom), types de contrat (CDI/CDD), salaire > 0, année de naissance 1940–2005, date d'embauche ≤ aujourd'hui, embauche postérieure à la naissance |
| `sportpratique` | Sport non nul, intégrité référentielle avec `salarie`, sport reconnu par le moteur de génération |
| `salarie_geocode` | Couverture complète (autant de lignes que de salariés), coordonnées dans le bounding box France métropolitaine (lat 41–51,5 / lng -5,5–9,5), cohérence distance / seuil / éligibilité |
| `strava` | Ignorée (table vide à cette étape) |
| `strava_comment` | Ignorée (table vide à cette étape) |

### Étape 5 — `generate_strava_raw.py` (bronze)

Génère 12 mois d'activités sportives simulées pour chaque salarié pratiquant un sport, et les stocke **brutes** (format JSON API Strava), sans transformation.

```
1. Crée des IDs athlètes uniques (6 chiffres) → table athlete
2. Associe chaque salarié sportif à un athlète   → table salarieathlete
3. Génère 15 à 80 activités par salarié          → table strava_raw
4. Génère des commentaires (30 % de probabilité) → table strava_comment_raw
```

**Contraintes de génération :**
- Uniquement en semaine (lundi–vendredi), entre 06h00 et 19h59
- `elapsed_time = moving_time + delta aléatoire 0–15 min`
- Matching du sport insensible aux accents et à la casse, avec fallback par sous-chaîne
- JSON simulés via `simulate_activity_json()` et `simulate_comments_json()` (couche ETL partagée), au format qu'aurait renvoyé l'API Strava réelle
- Chaque ligne de `strava_raw` / `strava_comment_raw` est marquée `processed = FALSE` à l'insertion

**Métriques par sport (générées par `utils/strava_generation.py`) :**

| Sport | Distance (m) | Durée (min) | Vitesse moy. (km/h) | Watts |
|---|---|---|---|---|
| Course à pied / Running | calculée depuis vitesse × temps | 15 – 150 | 7 – 20 | — |
| Randonnée | calculée depuis vitesse × temps | 15 – 120 | 4 – 9 | — |
| Vélo | calculée depuis vitesse × temps | 30 – 300 | 15 – 35 | avg 100–300 / max 200–600 |
| Natation | 500 – 5 000 | 20 – 90 | — | — |
| Voile | 5 000 – 50 000 | 120 – 480 | — | — |
| Triathlon | 10 000 – 200 000 | 60 – 360 | — | — |
| Football / Rugby / Basketball | — | 60 – 120 | — | — |
| Tennis | — | 45 – 180 | — | — |
| Badminton / Tennis de table | — | 45 – 120 | — | — |
| Escalade / Équitation | — | 60 – 180 | — | — |
| Judo / Boxe | — | 60 – 120 | — | — |

> Pour les sports avec vitesse définie, la distance est calculée à partir de `vitesse × moving_time` pour assurer la cohérence des données. Pour les sports sans vitesse mais avec une plage de distance (natation, voile, triathlon), la distance est tirée aléatoirement dans la plage.

### Étape 6 — `etl_strava.py` (gold)

Transforme les enregistrements bruts de `strava_raw` / `strava_comment_raw` non encore traités (`processed = FALSE`) et les insère dans les tables métier.

```
1. Lit les activités non traitées par lots de 500 (ORDER BY inserted_at)
2. Parse le JSON via parse_activity_and_comments()   → tuples prêts pour PostgreSQL
3. Insère via insert_parsed_activity()                → strava + stravathlete + strava_comment
4. Marque la ligne source processed = TRUE (commit par activité)
```

- En cas d'erreur sur une ligne, celle-ci n'est pas marquée traitée et sera rejouée au prochain appel (idempotent), les autres lignes du lot continuent
- Ce script est aussi la seconde étape du flux temps réel (`pipeline_live.py`) : c'est l'insertion dans `strava` qui déclenche Debezium → Redpanda → Slack

### Étape 7 — `data_quality_check.py` (passe 2)

Même script que l'étape 4, exécuté après la génération et la transformation Strava. Cette fois la table `strava` est peuplée et validée.

| Table | Validations supplémentaires |
|---|---|
| `strava` | `id_strava` unique, `sport_type` / `start_date` / `end_date` non nuls, `moving_time` ≥ 1, `elapsed_time` ≥ `moving_time`, `end_date` > `start_date`, `avg_watt` ≤ `max_watt`, distances et vitesses positives quand présentes |
| `strava_comment` | `id_comment` unique et non nul, `id_strava` non nul, `created_at` non nul |

---

## Mise à jour des données salariés — update_salaries.py

Script à utiliser lorsque le fichier Données+RH.xlsx est modifié (changement d'adresse, de moyen de déplacement, de salaire...). Exécute 3 étapes séquentielles avec
arrêt immédiat en cas d'échec.

```bash
docker compose run --rm pipeline python update_salaries.py
```

### Étapes exécutées

1. scripts/import_excel.py       — upsert des données RH (ON CONFLICT DO UPDATE)
2. scripts/geocode_adresses.py   — regéocodage des adresses modifiées uniquement
3. scripts/data_quality_check.py — validation qualité post-mise à jour

> generate_strava_raw.py et etl_strava.py ne sont pas relancés : la mise à jour des données RH est indépendante des activités sportives déjà générées.

### Quand relancer quoi ?

| Modification | Action requise |
|---|---|
| Adresse domicile | `update_salaries.py` |
| Moyen de déplacement | `update_salaries.py` |
| Seuils de distance `(config.py)` | `docker compose run --rm pipeline python -m scripts.geocode_adresses` |
| Taux de prime | Aucune (avec PowerBI) |
| Seuils d'activités (15 par défaut) | Aucune (avec PowerBI) |


## Flux temps réel — CDC vers Slack

### Capture des changements (Debezium)

PostgreSQL est configuré avec `wal_level=logical`. Le connecteur Debezium surveille la table `strava` et publie chaque insertion dans Redpanda (topic `sport.public.strava`).

```
PostgreSQL (WAL) → Debezium → Redpanda → consumer_slack.py → Slack webhook
```

### `consumer_slack.py`

Consumer Kafka en mode batch (timeout 5 s sans message) déclenché périodiquement par Kestra.

- Valide la présence de `SLACK_WEBHOOK_URL` au démarrage
- Connexion PostgreSQL protégée par `try/except` et `try/finally`
- Pour chaque message CDC (`payload.after`) :
  - Remonte le salarié via `strava → stravathlete → salarieathlete → salarie`
  - Formate un message Slack enrichi (durée, distance, vitesse, puissance selon le sport)
  - Envoie via webhook

**Exemple de notification :**
```
🎉 Félicitations à Prénom Nom pour avoir fait du Running pendant 45 min !

📊 Quelques chiffres :
📏 Distance : 8,3 km
⚡ Vitesse moy. : 11,1 km/h
🚀 Pointe max : 14,2 km/h

💬 Reprise du sport :)

💪 Maintenant, à qui le tour ?
```

### `pipeline_live.py`

Orchestrateur du flux temps réel, équivalent de `run_pipeline.py` pour la simulation d'une nouvelle activité. Exécute dans l'ordre, avec arrêt immédiat en cas d'échec :

```
1. scripts/simulate_strava_activity.py   — bronze : génère et stocke une activité brute
2. scripts/etl_strava.py                 — gold   : transforme et déclenche Debezium → Redpanda → Slack
```

```bash
python pipeline_live.py
```

### `simulate_strava_activity.py`

Dépose une activité brute pour un salarié sportif tiré au sort (couche bronze uniquement — ne déclenche pas encore le CDC).

- Sélectionne un athlète au hasard via `ORDER BY random() LIMIT 1`
- Génère les métriques via la couche partagée `strava_generation.py`
- Simule les JSONs via `simulate_activity_json()` / `simulate_comments_json()` (couche ETL partagée)
- Vérifie l'unicité de `id_strava` en base dans `strava` **et** `strava_raw`
- Insère dans `strava_raw` (+ `strava_comment_raw` si commentaire) — non exécuté seul en production, appelé par `pipeline_live.py`

### `etl_strava.py` (flux live)

Deuxième étape de `pipeline_live.py` : transforme la ligne brute déposée par `simulate_strava_activity.py` et l'insère dans `strava` (+ `stravathlete` / `strava_comment`). C'est cette insertion dans `strava` qui déclenche le flux CDC complet.

---

## Couche ETL partagée — `utils/strava_etl.py`

Centralise la logique d'intégration Strava, utilisée par `generate_strava_raw.py`, `simulate_strava_activity.py` (simulation JSON) et `etl_strava.py` (parsing + insertion).

| Fonction | Rôle |
|---|---|
| `simulate_activity_json()` | Construit un dict au format `DetailedActivity` (API Strava v3) |
| `simulate_comments_json()` | Construit une liste de commentaires (30 % de probabilité) |
| `parse_activity_and_comments()` | Parse les JSONs et retourne des tuples prêts pour PostgreSQL |
| `insert_parsed_activity()` | Insère dans `strava`, `stravathlete` et `strava_comment` |

> En production, `simulate_activity_json` et `simulate_comments_json` sont remplacés par des appels réels à l'API Strava v3. La couche ETL (`parse_activity_and_comments` + `insert_parsed_activity`) reste identique.

---

## Orchestration — Kestra

Le workflow `flows/notify_slack_strava.yml` exécute `consumer_slack.py` toutes les minutes pour consommer les messages Redpanda et envoyer les notifications.

Interface web accessible sur `http://localhost:8080`.

### Initialisation de l'offset Redpanda

Pour éviter que le consumer Slack n'envoie les milliers de messages historiques lors du premier lancement, positionner l'offset du groupe à la fin du topic 
avant d'activer le flow :

```bash
docker compose exec redpanda rpk group seek slack-notifier --topics sport.public.strava --to end --allow-new-topics
```

---

## Services Docker

| Service | Image | Port | Rôle |
|---|---|---|---|
| `postgres` | postgres:17 | 5433 | Base de données principale (wal_level=logical) |
| `redpanda` | redpandadata/redpanda:v26.1.1 | 19092 | Message broker Kafka-compatible |
| `redpanda-console` | redpandadata/console | 8082 | UI Redpanda |
| `connect` | debezium/connect:2.7 | 8083 | Kafka Connect + Debezium |
| `debezium-setup` | curlimages/curl | — | Enregistrement du connecteur (one-shot) |
| `kestra` | kestra/kestra:latest | 8080 | Orchestrateur de workflows |
| `pipeline` | (Dockerfile local) | — | Exécution du pipeline Python |

---

## Gestion des erreurs et logs

| Niveau | Déclencheur | Comportement |
|---|---|---|
| `[CRITICAL]` | Échec connexion DB / Kafka / validation bloquante | Arrêt immédiat |
| `[ERROR]` | Échec insertion / envoi Slack | Rollback, poursuite |
| `[WARNING]` | Fallback géocodage, fichiers multiples, géocodage sans résultat | Continue avec alternative |
| `[INFO]` | Progression normale | Compteurs et statistiques |

Tous les logs sont écrits en UTF-8, simultanément en console et dans `logs/`.

---

## Exécution des scripts

```bash
# Pipeline complet (7 étapes)
docker compose run --rm pipeline python run_pipeline.py

# Flux temps réel (1 activité simulée → Slack)
docker compose run --rm pipeline python pipeline_live.py

# Mise à jour des données salariés (après modification du fichier Excel)
docker compose run --rm pipeline python update_salaries.py

# Scripts individuels
docker compose run --rm pipeline python scripts/analyse_rh.py
docker compose run --rm pipeline python scripts/import_excel.py
docker compose run --rm pipeline python scripts/geocode_adresses.py
docker compose run --rm pipeline python scripts/data_quality_check.py
docker compose run --rm pipeline python -m scripts.generate_strava_raw
docker compose run --rm pipeline python -m scripts.etl_strava
docker compose run --rm pipeline python -m scripts.consumer_slack
```

---

## Tests unitaires

`tests/test_unitaires.py` couvre les fonctions pures du projet (pas de DB, pas de réseau) : normalisation des sports et des adresses, résolution des règles par sport, génération des métriques d'activité, parsing des JSON Strava simulés, filtrage des sports valides, conversion des dates Excel, et cohérence des seuils d'éligibilité avec ce README. Complémentaire aux validations Great Expectations (`utils/data_quality.py`), qui valident la donnée à l'exécution plutôt que la logique du code.

`tests/conftest.py` ajoute la racine du projet à `sys.path` pour permettre l'import des modules `utils/`/`scripts/` depuis les tests, et neutralise `setup_logging()` (qui entrerait sinon en conflit avec la capture de sortie de pytest).

**Exécution locale :**
```bash
pip install -r requirements.txt
pytest tests/ -v
```

**Exécution via Docker :**
```bash
docker compose build pipeline   # si requirements.txt ou tests/ ont changé
docker compose run --rm pipeline pytest tests/ -v
```

---

## Données simulées

- **161 salariés** importés depuis Excel, dont 95 salariés sportifs concernés par la génération Strava
- **15 à 80 activités** générées par salarié sportif sur 12 mois
- Activités limitées aux jours ouvrés, horaires 06h00–19h59
- **30 % des activités** comportent un commentaire Strava simulé
- Métriques cohérentes par type de sport :
  - Distance calculée depuis vitesse × temps pour running, randonnée, vélo
  - Watts générés uniquement pour le vélo
  - Pas de distance ni de vitesse pour les sports collectifs et de combat
