-- Version Docker : pulsevent_user est déjà créé automatiquement par
-- l'image officielle PostgreSQL via la variable d'environnement POSTGRES_USER.
-- Ce script ne fait que créer le rôle de groupe et lui attribuer les droits


-- Création du rôle applicatif pulsevent_role (rôle de groupe, sans droit de connexion)
CREATE ROLE pulsevent_role;

-- Attribution des droits sur la base pulsevent
GRANT CONNECT ON DATABASE pulsevent TO pulsevent_role;
GRANT USAGE ON SCHEMA public TO pulsevent_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pulsevent_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pulsevent_role;

-- Attribution du rôle pulsevent_role à l'utilisateur pulsevent_user
GRANT pulsevent_role TO pulsevent_user;