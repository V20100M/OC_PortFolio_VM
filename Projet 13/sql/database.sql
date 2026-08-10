-- Création de la base de données Puls-Events
-- À exécuter une seule fois, connecté en tant que superutilisateur (ex: postgres)
-- Exemple : psql -U postgres -f sql/database.sql

CREATE DATABASE pulsevent
    WITH
    ENCODING = 'UTF8'
    LC_COLLATE = 'fr_FR.UTF-8'
    LC_CTYPE = 'fr_FR.UTF-8'
    TEMPLATE = template0;

-- Remarque : si la base existe déjà, cette commande renverra une erreur
-- "database already exists" — c'est normal, ignorez-la dans ce cas.