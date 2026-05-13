CREATE TABLE IF NOT EXISTS raw.artists (
    artist_id  VARCHAR PRIMARY KEY,
    name       VARCHAR NOT NULL,
    genres     VARCHAR NOT NULL DEFAULT '[]',
    fetched_at TIMESTAMPTZ
);