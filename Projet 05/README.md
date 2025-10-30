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

Lors du démarrage du projet :
- Le conteneur MongoDB est créé et initialisé avec des rôles et utilisateurs définis dans le script data/init/01-medical-roles-users.js.
- Une fois la base prête, le conteneur medical_data_migration exécute automatiquement le script create_and_import_medical_data.py, qui :
  1) vérifie la cohérence du fichier CSV via test_integrity.py,
  2) attend que MongoDB soit totalement opérationnel,
  3) crée la collection admissions avec un schéma JSON de validation,
  4) applique un index unique sur les patients,
  5) nettoie et insère les données,
  6) ignore les doublons et affiche un rapport final.

Ce pipeline garantit une migration fiable, traçable et automatisée.

## 🧱 Architecture du projet

```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── create_and_import_medical_data.py     # Script principal de migration
├── test_integrity.py                     # Vérification des données CSV
├── medical_data.csv                      # Jeu de données source
├── .env                                  # Variables d'environnement
├── .dockerignore                         # Exclusion de fichiers inutiles lors du build
└── data/
    ├── db/                               # Volume persistant pour les données MongoDB (créé par MongoDB)
    └── init/
        └── 01-medical-roles-users.js     # Script JS d’initialisation des rôles/utilisateurs
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

Lors du **premier démarrage**, MongoDB exécute automatiquement le script :
data/init/01-medical-roles-users.js

Ce script crée sur la base `medical_data` :
- les rôles applicatifs (`medical_admin`, `medical_user`, etc.),
- et les utilisateurs associés (`admin_medical`, `user_medical`, etc.).

> ⚠️ Le script n’est exécuté **que si le répertoire `data/db` est vide**, c'est-à-dire, à la première exécution.  
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
Pour constuire l'image, deux possibilités :  
- docker compose build (donnera un nom par défaut contenant en partie le nom du répertoire)
- docker compose -p nom_spécifique --build (donnera nom_spécifique comme nom)

Ici nous utiliserons docker-med-import comme nom donc la commande suivante :
```
docker compose -p docker-med-import up --build
```
Cette commande exécute le fichier docker-compose.yml qui :
- construit l’image du conteneur Python,
- lance MongoDB avec initialisation,
- exécute le script d’import create_and_import_medical_data.py.

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
```

## 🧭 Connexion à MongoDB depuis l’hôte
Depuis le terminal
```
mongosh "mongodb://root_admin:Root@123@localhost:27017/admin?authSource=admin"
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
- les valeurs nulles et les dates incorrectes.
En cas d’erreur, la migration est stoppée pour garantir l’intégrité des données.