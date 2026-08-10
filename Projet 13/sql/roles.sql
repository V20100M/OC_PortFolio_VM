-- Ce script ne fait que créer le rôle de groupe et lui attribuer les droits


-- Création du rôle applicatif pulsevent_role (rôle de groupe, sans droit de connexion)
CREATE ROLE pulsevent_role;

-- Attribution des droits sur la base pulsevent
GRANT CONNECT ON DATABASE pulsevent TO pulsevent_role;
GRANT USAGE ON SCHEMA public TO pulsevent_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pulsevent_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pulsevent_role;

-- Création de l'utilisateur applicatif pulsevent_user (rôle de connexion, avec mot de passe)
CREATE ROLE pulsevent_user LOGIN PASSWORD 'Puls3v3ntUs3r!';

-- Attribution du rôle pulsevent_role à l'utilisateur pulsevent_user
GRANT pulsevent_role TO pulsevent_user;