CREATE TABLE IF NOT EXISTS raw.artists_genres (
    artist_id INTEGER NOT NULL,
    genre_id  INTEGER NOT NULL,
    PRIMARY KEY (artist_id, genre_id)
);
