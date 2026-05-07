"""Load environment configuration for Spotify credentials."""

import os

from dotenv import load_dotenv

load_dotenv(".config/.env")

CLIENT_ID = os.environ["SPOTIPY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIPY_CLIENT_SECRET"]
REDIRECT_URI = os.environ["SPOTIPY_REDIRECT_URI"]
PLAYLIST_ID = os.environ["PLAYLIST_ID"]
CACHE_PATH = ".config/.cache"
