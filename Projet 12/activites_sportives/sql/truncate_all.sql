-- Script : truncate_all.sql
-- Description : Script pour vider toutes les tables de la base de données
-- en respectant les contraintes de clés étrangères (CASCADE)
-- A exécuter depuis un outil de gestion de base de données (ex : psql, pgAdmin)

TRUNCATE TABLE strava_comment_raw CASCADE;
TRUNCATE TABLE strava_raw CASCADE;
TRUNCATE TABLE strava_comment CASCADE;
TRUNCATE TABLE stravathlete CASCADE;
TRUNCATE TABLE strava CASCADE;
TRUNCATE TABLE salarieathlete CASCADE;
TRUNCATE TABLE athlete CASCADE;
TRUNCATE TABLE sportpratique CASCADE;
TRUNCATE TABLE salarie_geocode CASCADE;
TRUNCATE TABLE salarie CASCADE;
