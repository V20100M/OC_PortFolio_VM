-- Couche Bronze : donnees brutes, telles que recues d'Open Agenda
-- Deduplication sur (uid, updated_at_source) : un evenement inchange
-- depuis le dernier import n'est pas re-insere ; une vraie mise a jour
-- source cree une nouvelle ligne (historique Bronze preserve).
CREATE TABLE IF NOT EXISTS evenements_bronze (
    id                  SERIAL NOT NULL,
    uid                 BIGINT NOT NULL,
    raw_data            JSONB NOT NULL,
    updated_at_source   TIMESTAMPTZ NOT NULL,
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed           BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE evenements_bronze OWNER TO pulsevent_user;
ALTER TABLE ONLY evenements_bronze ADD CONSTRAINT pk_evenements_bronze PRIMARY KEY (id);
ALTER TABLE ONLY evenements_bronze ADD CONSTRAINT uq_bronze_uid_updated UNIQUE (uid, updated_at_source);
CREATE INDEX idx_evenements_bronze_uid ON evenements_bronze(uid);
CREATE INDEX idx_evenements_bronze_processed ON evenements_bronze(processed);

-- Couche Gold : donnees nettoyees, pretes a etre vectorisees
-- Un seul enregistrement par uid (etat le plus recent), mis a jour via
-- ON CONFLICT (uid) DO UPDATE dans load_gold.py.
CREATE TABLE IF NOT EXISTS evenements_gold (
    uid                  BIGINT NOT NULL,
    title_fr             TEXT NOT NULL,
    description_fr       TEXT,
    longdescription_fr   TEXT,
    firstdate_begin      TIMESTAMPTZ,
    lastdate_end         TIMESTAMPTZ,
    location_name        TEXT,
    location_city        TEXT,
    location_department  TEXT,
    location_region      TEXT,
    location_address     TEXT,
    conditions_fr        TEXT,
    keywords_fr          TEXT,
    updated_at_source    TIMESTAMPTZ,
    transformed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_to_qdrant       BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE evenements_gold OWNER TO pulsevent_user;
ALTER TABLE ONLY evenements_gold ADD CONSTRAINT pk_evenements_gold PRIMARY KEY (uid);
CREATE INDEX idx_evenements_gold_sent ON evenements_gold(sent_to_qdrant);

GRANT SELECT, INSERT, UPDATE, DELETE ON evenements_bronze, evenements_gold TO pulsevent_role;
GRANT USAGE, SELECT ON SEQUENCE evenements_bronze_id_seq TO pulsevent_role;