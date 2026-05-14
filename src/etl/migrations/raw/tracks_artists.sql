CREATE TABLE IF NOT EXISTS raw.tracks_artists (
    track_id  INTEGER NOT NULL,
    artist_id INTEGER NOT NULL,
    PRIMARY KEY (track_id, artist_id)
);
