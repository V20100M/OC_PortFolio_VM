-- Base de donnees dediee a l'etat interne de Kestra (executions, triggers,
-- historique des flows) distincte de "pulsevent" (donnees applicatives),
-- meme instance PostgreSQL.

CREATE DATABASE kestra OWNER pulsevent_user;

\connect kestra
GRANT ALL ON SCHEMA public TO pulsevent_user;