CREATE SEQUENCE IF NOT EXISTS tracks_id_seq;

CREATE TABLE IF NOT EXISTS raw.tracks (
    id           INTEGER DEFAULT nextval('tracks_id_seq') PRIMARY KEY,
    track_uri    VARCHAR NOT NULL UNIQUE,
    name         VARCHAR,
    release_year INTEGER,
    album_name   VARCHAR,
    album_id     VARCHAR,
    inserted_at  TIMESTAMP,
    updated_at   TIMESTAMP
);
