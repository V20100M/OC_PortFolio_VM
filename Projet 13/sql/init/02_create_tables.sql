-- Création des tables de Puls-Events
-- À exécuter connecté à la base "pulsevent", après roles.sql
-- exécuté automatiquement au premier démarrage du conteneur PostgreSQL (dossier docker-entrypoint-initdb.d).

CREATE TABLE public.utilisateurs (
    id_utilisateur  SERIAL NOT NULL,
    nom             VARCHAR(100) NOT NULL,
    prenom          VARCHAR(100) NOT NULL,
    age             SMALLINT CHECK (age >= 0 AND age <= 120),
    code_postal     VARCHAR(10),
    ville           VARCHAR(150),
    mail            VARCHAR(255) NOT NULL UNIQUE
);

ALTER TABLE public.utilisateurs OWNER TO pulsevent_user;


CREATE TABLE public.identifiants (
    id_utilisateur  INTEGER NOT NULL,
    login           VARCHAR(100) NOT NULL UNIQUE,
    mdp_hash        VARCHAR(255) NOT NULL
);

ALTER TABLE public.identifiants OWNER TO pulsevent_user;


CREATE TABLE public.historiques_chatbot (
    id               SERIAL NOT NULL,
    id_utilisateur   INTEGER,
    conversation_id  UUID NOT NULL,
    date_echange     TIMESTAMPTZ NOT NULL DEFAULT now(),
    role             VARCHAR(20) NOT NULL,
    texte            TEXT NOT NULL
);

ALTER TABLE public.historiques_chatbot OWNER TO pulsevent_user;


ALTER TABLE ONLY public.utilisateurs
    ADD CONSTRAINT pk_utilisateurs PRIMARY KEY (id_utilisateur);

ALTER TABLE ONLY public.identifiants
    ADD CONSTRAINT pk_identifiants PRIMARY KEY (id_utilisateur);

ALTER TABLE ONLY public.historiques_chatbot
    ADD CONSTRAINT pk_historiques_chatbot PRIMARY KEY (id);

ALTER TABLE ONLY public.identifiants
    ADD CONSTRAINT fk_identifiants_utilisateur FOREIGN KEY (id_utilisateur) REFERENCES public.utilisateurs(id_utilisateur) ON DELETE CASCADE;

ALTER TABLE ONLY public.historiques_chatbot
    ADD CONSTRAINT fk_historiques_utilisateur FOREIGN KEY (id_utilisateur) REFERENCES public.utilisateurs(id_utilisateur) ON DELETE CASCADE;

ALTER TABLE ONLY public.historiques_chatbot
    ADD CONSTRAINT chk_historiques_role CHECK (role IN ('utilisateur', 'assistant'));

CREATE INDEX idx_historiques_id_utilisateur ON public.historiques_chatbot(id_utilisateur);
CREATE INDEX idx_historiques_conversation ON public.historiques_chatbot(conversation_id);
CREATE INDEX idx_utilisateurs_mail ON public.utilisateurs(mail);


GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pulsevent_role;
GRANT USAGE, SELECT ON SEQUENCE public.utilisateurs_id_utilisateur_seq TO pulsevent_role;
GRANT USAGE, SELECT ON SEQUENCE public.historiques_chatbot_id_seq TO pulsevent_role;