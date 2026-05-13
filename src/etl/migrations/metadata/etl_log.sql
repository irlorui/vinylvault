CREATE SEQUENCE IF NOT EXISTS etl_log_id_seq;

CREATE TABLE IF NOT EXISTS metadata.etl_log (
    id          INTEGER DEFAULT nextval('etl_log_id_seq') PRIMARY KEY,
    playlist_id VARCHAR,
    status      VARCHAR NOT NULL,
    tracks_processed     INTEGER,
    error       VARCHAR,
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    last_track_added_at TIMESTAMP NOT NULL
);