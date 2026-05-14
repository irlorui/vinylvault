CREATE TABLE IF NOT EXISTS raw.playlist_tracks (
    playlist_id INTEGER NOT NULL,
    track_id    INTEGER NOT NULL,
    position    INTEGER,
    PRIMARY KEY (playlist_id, track_id)
);
