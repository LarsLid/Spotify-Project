"""Saves your last 50 Spotify plays to data/recent_plays.csv.

Run it regularly (e.g. hourly with Windows Task Scheduler) to build a
continuous listening log. Run it manually once first so you can log in.
"""
from pathlib import Path

import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Task Scheduler runs scripts from another folder, so use paths relative
# to this file instead of the current working directory.
BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="user-top-read user-read-recently-played playlist-read-private",
    cache_path=str(BASE / ".cache"),
))

history_file = BASE / "data" / "recent_plays.csv"
history_file.parent.mkdir(exist_ok=True)

items = sp.current_user_recently_played(limit=50)["items"]
new = pd.DataFrame([{
    "played_at": it["played_at"],
    "track": it["track"]["name"],
    "artist": it["track"]["artists"][0]["name"],
    "album": it["track"]["album"]["name"],
    "duration_ms": it["track"]["duration_ms"],
    "track_uri": it["track"]["uri"],
} for it in items])

if history_file.exists():
    old = pd.read_csv(history_file)
    before = len(old)
    combined = pd.concat([old, new], ignore_index=True)
else:
    before = 0
    combined = new

combined = combined.drop_duplicates(subset=["played_at", "track_uri"]).sort_values("played_at")
combined.to_csv(history_file, index=False)

print(f"{len(combined) - before} new plays added, {len(combined)} in total.")
