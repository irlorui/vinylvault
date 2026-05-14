CREATE SEQUENCE IF NOT EXISTS playlists_id_seq;

CREATE TABLE IF NOT EXISTS raw.playlists (
    id           INTEGER DEFAULT nextval('playlists_id_seq') PRIMARY KEY,
    playlist_uri VARCHAR NOT NULL UNIQUE,
    name         VARCHAR,
    etl_run_at   TIMESTAMP
);
