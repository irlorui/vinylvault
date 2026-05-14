CREATE SEQUENCE IF NOT EXISTS genres_id_seq;

CREATE TABLE IF NOT EXISTS raw.genres (
    id   INTEGER DEFAULT nextval('genres_id_seq') PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE
);
