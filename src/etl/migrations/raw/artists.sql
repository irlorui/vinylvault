CREATE SEQUENCE IF NOT EXISTS artists_id_seq;

CREATE TABLE IF NOT EXISTS raw.artists (
    id         INTEGER DEFAULT nextval('artists_id_seq') PRIMARY KEY,
    artist_uri VARCHAR NOT NULL UNIQUE,
    name       VARCHAR,
    fetched_at TIMESTAMP
);
