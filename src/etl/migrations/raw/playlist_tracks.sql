CREATE TABLE IF NOT EXISTS raw.playlist_tracks (
    playlist_id VARCHAR NOT NULL,
    track_id    VARCHAR NOT NULL,
    position    INTEGER,
    PRIMARY KEY (playlist_id, track_id)
);