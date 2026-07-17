\connect activitessportives

SET default_tablespace = '';

SET default_table_access_method = heap;


CREATE TABLE public.athlete (
    id_athlete integer NOT NULL
);

ALTER TABLE public.athlete OWNER TO sport_user;


CREATE TABLE public.salarie (
    id_salarie integer NOT NULL,
    nom character varying(200) NOT NULL,
    prenom character varying(200) NOT NULL,
    date_naissance date NOT NULL,
    bu character varying(200) NOT NULL,
    date_embauche date NOT NULL,
    salaire_brut numeric(10,2) NOT NULL,
    type_contrat character varying(50) NOT NULL,
    jours_cp integer NOT NULL,
    adresse_domicile character varying(255) NOT NULL,
    moyen_deplacement character varying(100) NOT NULL
);

ALTER TABLE public.salarie OWNER TO sport_user;


CREATE TABLE public.sportpratique (
    id_salarie integer NOT NULL,
    pratique_sport character varying(200)
);

ALTER TABLE public.sportpratique OWNER TO sport_user;


CREATE TABLE public.strava (
    id_strava bigint NOT NULL,
    start_date timestamp without time zone NOT NULL,
    end_date timestamp without time zone,
    sport_type character varying(100) NOT NULL,
    distance double precision,
    moving_time integer,
    elapsed_time integer,
    avg_speed double precision,
    max_speed double precision,
    avg_watt double precision,
    max_watt double precision
);

ALTER TABLE public.strava OWNER TO sport_user;


CREATE TABLE public.salarieathlete (
    id_salarie integer NOT NULL,
    id_athlete integer NOT NULL
);

ALTER TABLE public.salarieathlete OWNER TO sport_user;


CREATE TABLE public.stravathlete (
    id_strava bigint NOT NULL,
    id_athlete integer NOT NULL
);

ALTER TABLE public.stravathlete OWNER TO sport_user;


CREATE TABLE public.salarie_geocode (
    id_salarie INTEGER NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    geocode_ok BOOLEAN NOT NULL DEFAULT FALSE,
    distance_km FLOAT,
    eligible_prime BOOLEAN
);

ALTER TABLE public.salarie_geocode OWNER TO sport_user;


CREATE TABLE public.strava_comment (
    id_comment  BIGINT NOT NULL,
    id_strava   BIGINT NOT NULL,
    texte       TEXT,
    auteur      VARCHAR(255),
    created_at  TIMESTAMP
);

ALTER TABLE public.strava_comment OWNER TO sport_user;


CREATE TABLE public.strava_raw (
    id           BIGSERIAL NOT NULL,
    id_strava    BIGINT    NOT NULL,
    raw_activity JSONB     NOT NULL,
    inserted_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    processed    BOOLEAN   NOT NULL DEFAULT FALSE
);

ALTER TABLE public.strava_raw OWNER TO sport_user;


CREATE TABLE public.strava_comment_raw (
    id          BIGSERIAL NOT NULL,
    id_strava   BIGINT    NOT NULL,
    raw_comment JSONB     NOT NULL,
    inserted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed   BOOLEAN   NOT NULL DEFAULT FALSE
);

ALTER TABLE public.strava_comment_raw OWNER TO sport_user;


ALTER TABLE ONLY public.athlete
    ADD CONSTRAINT pk_athlete PRIMARY KEY (id_athlete);


ALTER TABLE ONLY public.salarie
    ADD CONSTRAINT pk_salarie PRIMARY KEY (id_salarie);


ALTER TABLE ONLY public.sportpratique
    ADD CONSTRAINT pk_sportpratique PRIMARY KEY (id_salarie);


ALTER TABLE ONLY public.strava
    ADD CONSTRAINT pk_strava PRIMARY KEY (id_strava);


ALTER TABLE ONLY public.salarieathlete
    ADD CONSTRAINT pk_salarieathlete PRIMARY KEY (id_salarie);


ALTER TABLE ONLY public.stravathlete
    ADD CONSTRAINT pk_stravathlete PRIMARY KEY (id_strava);


ALTER TABLE ONLY public.salarie_geocode
    ADD CONSTRAINT pk_salarie_geocode PRIMARY KEY (id_salarie);


ALTER TABLE ONLY public.strava_comment
    ADD CONSTRAINT pk_strava_comment PRIMARY KEY (id_comment);


ALTER TABLE ONLY public.strava_raw
    ADD CONSTRAINT pk_strava_raw PRIMARY KEY (id);


ALTER TABLE ONLY public.strava_comment_raw
    ADD CONSTRAINT pk_strava_comment_raw PRIMARY KEY (id);


ALTER TABLE ONLY public.sportpratique
    ADD CONSTRAINT fk_sportpratique_salarie FOREIGN KEY (id_salarie) REFERENCES public.salarie(id_salarie);


ALTER TABLE ONLY public.salarieathlete
    ADD CONSTRAINT fk_salarieathlete_athlete FOREIGN KEY (id_athlete) REFERENCES public.athlete(id_athlete);


ALTER TABLE ONLY public.salarieathlete
    ADD CONSTRAINT fk_salarieathlete_salarie FOREIGN KEY (id_salarie) REFERENCES public.salarie(id_salarie);


ALTER TABLE ONLY public.stravathlete
    ADD CONSTRAINT fk_stravathlete_athlete FOREIGN KEY (id_athlete) REFERENCES public.athlete(id_athlete);


ALTER TABLE ONLY public.stravathlete
    ADD CONSTRAINT fk_stravathlete_strava FOREIGN KEY (id_strava) REFERENCES public.strava(id_strava);


ALTER TABLE ONLY public.salarie_geocode
    ADD CONSTRAINT fk_salarie_geocode_salarie FOREIGN KEY (id_salarie) REFERENCES public.salarie(id_salarie);


ALTER TABLE ONLY public.strava_comment
    ADD CONSTRAINT fk_strava_comment_strava FOREIGN KEY (id_strava) REFERENCES public.strava(id_strava);


GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sport_role;
GRANT USAGE, SELECT ON SEQUENCE public.strava_raw_id_seq TO sport_role;
GRANT USAGE, SELECT ON SEQUENCE public.strava_comment_raw_id_seq TO sport_role;