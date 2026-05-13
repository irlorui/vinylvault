CREATE TABLE IF NOT EXISTS raw.tracks (
    track_id          VARCHAR PRIMARY KEY,
    name              VARCHAR NOT NULL,
    release_year      INTEGER,
    album_name        VARCHAR,
    album_id          VARCHAR,
    artists           VARCHAR NOT NULL,
    genres            VARCHAR NOT NULL DEFAULT '[]',
    inserted_at       TIMESTAMP,
    updated_at        TIMESTAMP
);