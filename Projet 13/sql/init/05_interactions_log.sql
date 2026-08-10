CREATE TABLE interactions_log (
    id                SERIAL NOT NULL,
    id_utilisateur    INTEGER,
    conversation_id   UUID NOT NULL,
    date_heure        TIMESTAMPTZ NOT NULL DEFAULT now(),
    question          TEXT NOT NULL,
    reponse           TEXT NOT NULL,
    ville_initiale    VARCHAR(150),
    geo_field         VARCHAR(50),
    geo_value         VARCHAR(150),
    source_reponse    VARCHAR(20),
    latence_ms        INTEGER,
    feedback          VARCHAR(10)
);

ALTER TABLE interactions_log OWNER TO pulsevent_user;
ALTER TABLE ONLY interactions_log ADD CONSTRAINT pk_interactions_log PRIMARY KEY (id);
ALTER TABLE ONLY interactions_log ADD CONSTRAINT fk_interactions_utilisateur FOREIGN KEY (id_utilisateur) REFERENCES utilisateurs(id_utilisateur) ON DELETE SET NULL;
ALTER TABLE ONLY interactions_log ADD CONSTRAINT chk_source_reponse CHECK (source_reponse IN ('qdrant', 'web_search'));
ALTER TABLE ONLY interactions_log ADD CONSTRAINT chk_feedback CHECK (feedback IN ('positif', 'negatif') OR feedback IS NULL);

CREATE INDEX idx_interactions_conversation ON interactions_log(conversation_id);
CREATE INDEX idx_interactions_date ON interactions_log(date_heure);
CREATE INDEX idx_interactions_source ON interactions_log(source_reponse);

GRANT SELECT, INSERT, UPDATE, DELETE ON interactions_log TO pulsevent_role;
GRANT USAGE, SELECT ON SEQUENCE interactions_log_id_seq TO pulsevent_role;