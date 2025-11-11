# 🏥 Medical Data Migration – Migration automatisée vers MongoDB
## 📖 Description du projet

Ce projet permet d’automatiser la **migration de données médicales** à partir d’un fichier CSV vers une base **MongoDB**.  
L’environnement complet (base de données + script Python d’import) est conteneurisé avec Docker, garantissant une reproductibilité totale entre environnements (développement, test, production).

## 🎯 Objectifs

- Créer et initialiser automatiquement une base MongoDB contenant des rôles et utilisateurs personnalisés (via un script `.js`).
- Vérifier l’intégrité et la cohérence du jeu de données avant import (via schéma JSON de validation).
- Importer les données médicales depuis un fichier CSV dans une collection MongoDB dédiée.
- Garantir la portabilité et la reproductibilité du déploiement via des conteneurs.

## 💡 Fonctionnement global de la migration

Lors du lancement du Docker-Compose :

### 1️⃣ Le conteneur MongoDB démarre à partir de l'image officielle mongo 8.0
- lit les variables d'environnement du fichier .env (nom de la base, mot de passe, etc.) 
- initialise la base medical_data si data/db est vide
- exécute automatiquement les scripts présents dans data/init :
  - 01-medical-roles-users.js création des rôles et des utilisateurs
  - 02-create-collections.js création de la collection admissions avec schema JSON
- attend d'être prêt (healthcheck) avant de laisser l'autre conteneur démarrer.

### 2️⃣ le conteneur medical_data_migration (Python) démarre seulement une fois MongoDB "healthy"
Il :
- vérifie la cohérence du fichier CSV via test_integrity.py,  
- attend la disponibilité de MongoDB (script sh),  
- lit les variables d'environnement du fichier .env pour se connecter à la base,  
- nettoie et insère les données dans admissions,  
- gère les doublons et affiche un rapport final.  

## 🧱 Architecture du projet

```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── wait-for-mongo.sh                     # Vérifie la disponibilité de Mongo avant import
├── create_and_import_medical_data.py     # Script principal de migration
├── test_integrity.py                     # Vérification des données CSV
├── medical_data.csv                      # Jeu de données source
├── .env                                  # Variables d'environnement
├── .dockerignore                         # Exclusion de fichiers inutiles lors du build
└── data/
    ├── db/                               # Volume persistant MongoDB (créé au démarrage)
    └── init/                             # Scripts exécutés automatiquement à la première exécution
        └── 01-medical-roles-users.js     # Création des rôles et utilisateurs
        └── 02-create-collections.js      # Création de la collection et du schéma JSON
```


## 🧩 Technologies utilisées
[Docker](https://www.docker.com/) contient également Docker Compose  
[MongoDB](https://www.mongodb.com/products/self-managed/community-edition) Community Edition pour les tests locaux  
[MongoDB Compass](https://www.mongodb.com/products/tools/compass) pour une interface visuelle de MongoDB  
[MongoDB Shell](https://www.mongodb.com/try/download/shell)  
Python 3.10	sera installé via l’image officielle python:3.10-slim  
MongoDB 8.0 pour l'image MongoDB
Pandas pour la manipulation et nettoyage du fichier csv
PyMongo pour les interactions avec MongoDB


## 🔐 Initialisation de MongoDB

Lors du **premier démarrage**, MongoDB exécute automatiquement les scripts :
01-medical-roles-users.js

Ce script crée sur la base `medical_data` :
- les rôles applicatifs (`medical_admin`, `medical_user`, etc.),
- et les utilisateurs associés (`admin_medical`, `user_medical`, etc.).

02-create-collections.js

Crée la collection admissions avec son schéma JSON (validation structurelle et contrainte de types)

> ⚠️ Les scripts ne sont exécutés **que si le répertoire `data/db` est vide**, c'est-à-dire, à la première exécution.  
> Pour relancer une initialisation complète : supprimez `./data/db/` avant de relancer Docker.
---

## ⚙️ Configuration de l’environnement
Fichier .env :
```
MONGO_INITDB_ROOT_USERNAME=root_admin
MONGO_INITDB_ROOT_PASSWORD=Root@123
MONGO_INITDB_DATABASE=medical_data

APP_DB_USER=admin_medical
APP_DB_PASS_ENCODED=Admin%40123  # @ doit être encodé pour l’URI

MONGO_HOST=mongodb_medical
MONGO_PORT=27017
```
## 🐳 Déploiement avec Docker Compose

### 1️⃣ Vérification des outils
Vérifiez que Docker et Docker Compose sont installés en vérifiant leurs versions :
```
docker --version
docker compose version
```

### 2️⃣ Nettoyage préalable (optionnel mais recommandé)
```
docker compose down -v
Remove-Item -Recurse -Force .\data\db
```
### 3️⃣ Démarrage de l’environnement
Pour construire l'image, deux possibilités :  
- docker compose build (donnera un nom par défaut contenant en partie le nom du répertoire)
- docker compose -p nom_spécifique --build (donnera nom_spécifique comme nom)

Ici nous utiliserons docker-med-import comme nom donc la commande suivante :
```
docker compose -p docker-med-import up --build
```
Cette commande exécute le fichier docker-compose.yml qui :
- construit l’image du conteneur Python,
- démarre MongoDB et exécute les scripts d'initialisation,
- attend que MongoDB soit prêt via le healthcheck
- démarre le conteneur de migration qui exécute automatiquement le script Python d’import create_and_import_medical_data.py.

## 🔍 Vérification de la migration
### Voir les conteneurs actifs
```
docker ps -a
```

### Exemple de sortie attendue
```
🔍 Exécution du test d’intégrité des données...
✅ Fichier 'medical_data.csv' chargé avec succès.
✅ Toutes les colonnes attendues sont présentes. 
✅ Les types de colonnes principales sont corrects. 
✅ Aucune valeur manquante détectée. 
⚠️ 1068 doublons détectés (basés sur ['Name', 'Age', 'Gender', 'Blood Type', 'Date of Admission']). 
✅ 54966 documents insérés avec succès. 
⚠️ 534 doublons détectés et ignorés. 
📋 SYNTHÈSE DU TEST D’INTÉGRITÉ
---------------------------------------- 
Nombre total de lignes : 55500 
Colonnes présentes : 15
---------------------------------------- 
🏁 Test d’intégrité terminé.
✅ Test d’intégrité terminé — démarrage de la migration.

✅ Connexion MongoDB réussie.
✅ Collection 'admissions' prête (schéma déja défini dans l'initialisation MongoDB).
🔒 Index unique créé sur (patient.name, admission.date)
✅ 54966 documents insérés avec succès.
⚠️ 534 doublons détectés et ignorés.
📈 Nombre total de documents dans la collection : 54966
🎉 Import terminé avec vérification des doublons !
```

## 🧭 Connexion à MongoDB depuis l’hôte
Depuis le terminal (dans notre chaîne de connexion, dans le mot de passe @ est remplacé par %40)
```
mongosh "mongodb://admin_medical:Admin%40123@localhost:27017/medical_data?authSource=medical_data"
```

Depuis MongoDB Compass, dans URI :
```
mongodb://admin_medical:Admin%40123@localhost:27017/medical_data?authSource=medical_data
```
Autre méthode dans MongoDB Compass :
Mettre mongodb://localhost:27017/ dans URI, puis dans l'onglet Authentication :
- Username : admin_medical
- Password : Admin@123
- Authentication Database : medical_data

## 🧪 Test d’intégrité

Le script test_integrity.py est exécuté automatiquement avant la migration. Il vérifie :  
- la présence et cohérence des colonnes,
- le format des types de données,
- les valeurs nulles,
- la validité des dates et leur cohérence.
En cas d’erreur, la migration est stoppée pour garantir l’intégrité des données.  
  
Le script principal ne gère pas aussi bien les dates car il faut une stratégie d'actions pour les dates incohérentes.  
Un exemple d'action serait de les regrouper dans une collection à part pour les traiter et les corriger après validation des données.  

 ## 👥 Rôles et Utilisateurs

Dans ce projet, un utilisateur a été créé en rapport à un rôle pour montrer les possibilités d'action sur certaines données.  
Les rôles et les utilisateurs correspondants seront présentés en même temps.

Avant de créer un rôle, il faut bien indiquer dans quelle base de données nous nous plaçons :
```
use medical_data  (où medical_data est le nom de notre base de données)
```

Les titres suivants indiqueront le rôle / utilisateur.

### medical_admin / admin_medical

Rôle qui a beaucoup de droits, surtout la suppression de collection et de la base.

Rôle :
```
db.createRole({
  role: "medical_admin",
  privileges: [
    {
      resource: { db: "medical_data", collection: "" },
      actions: [ "find", "insert", "update", "remove", "createCollection", "createIndex", "dropCollection", "dropDatabase" ]
    }
  ],
  roles: []
})
```

Utilisateur :
```
db.createUser({
  user: "admin_medical",
  pwd: "Admin@123",
  roles: [ { role: "medical_admin", db: "medical_data" } ]
})
```

### medical_user / user_medical

Ce rôle correspond à un utilisateur classique (ici nous avons fait exprès de limiter ce rôle à une collection). Il peut ajouter, mettre à jour et lire des données, mais pas les supprimer.

Rôle :
```
db.createRole({
  role: "medical_user",
  privileges: [
    {
      resource: { db: "medical_data", collection: "admissions" },
      actions: [ "find", "insert", "update" ]
    }
  ],
  roles: []
})
```

Utilisateur :
```
db.createUser({
  user: "user_medical",
  pwd: "User@123",
  roles: [ { role: "medical_user", db: "medical_data" } ]
})
```

### medical_viewer / viewer_medical

Ce rôle permet uniquement la consultation de données.

Rôle :
```
db.createRole({
  role: "medical_viewer",
  privileges: [
    {
      resource: { db: "medical_data", collection: "" },
      actions: [ "find" ]
    }
  ],
  roles: []
})
```

Utilisateur :
```
db.createUser({
  user: "viewer_medical",
  pwd: "Viewer@123",
  roles: [ { role: "medical_viewer", db: "medical_data" } ]
})
```

### medical_indexer / indexer_medical

Ce rôle ne permet pas de consulter les données. Il peut modifier la structure de la base de données (nous avons limité les actions de suppression pour cette présentation).

Rôle :
```
db.createRole({
  role: "medical_indexer",
  privileges: [
    {
      resource: { db: "medical_data", collection: "" },
      actions: [ "createCollection", "createIndex", "collMod" ]
    }
  ],
  roles: []
})
```

Utilisateur :
```
db.createUser({
  user: "indexer_medical",
  pwd: "Indexer@123",
  roles: [ { role: "medical_indexer", db: "medical_data" } ]
})
```

Le projet définit 4 rôles illustratifs :

- medical_admin → full access (CRUD + structure)
- medical_user → CRUD sauf suppression
- medical_viewer → lecture seule
- medical_indexer → opérations structurelles (index, collections)

Chaque rôle a un utilisateur associé :

| Rôle             | Utilisateur      | Mot de passe | Permissions                                   |
|------------------|------------------|--------------|-----------------------------------------------|
| medical_admin    | admin_medical    | Admin@123    | Accès complet (CRUD + structure)              |
| medical_user     | user_medical     | User@123     | Lecture / Insertion / Mise à jour             |
| medical_viewer   | viewer_medical   | Viewer@123   | Lecture seule                                 |
| medical_indexer  | indexer_medical  | Indexer@123  | Opérations structurelles (index, collections) |

## ✅ Conclusion

Ce projet constitue un environnement de migration robuste, reproductible et professionnel :
- Initialisation automatique de la base
- Validation des schémas
- Import contrôlé
- Gestion complète des utilisateurs et rôles

A prévoir :
Il faudra une stratégie adaptée pour la gestion des dates incohérentes.