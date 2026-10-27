import os
from collections import Counter

import matplotlib.pyplot as plt
import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="user-top-read user-read-recently-played playlist-read-private"))

TIME_RANGES = {
    "short_term": "last 4 weeks",
    "medium_term": "last 6 months",
    "long_term": "all time (approx.)",
}

# --- 1. Top artists and tracks for each time range -------------------------
for key, label in TIME_RANGES.items():
    artists = sp.current_user_top_artists(limit=10, time_range=key)["items"]
    tracks = sp.current_user_top_tracks(limit=10, time_range=key)["items"]

    print(f"\n=== {label} ===")
    print("Top artists:")
    for i, a in enumerate(artists, 1):
        print(f"  {i:2}. {a['name']}")
    print("Top tracks:")
    for i, t in enumerate(tracks, 1):
        print(f"  {i:2}. {t['name']} - {t['artists'][0]['name']}")

# --- 2. Genre profile from your top 50 artists (long term) -----------------
top50 = sp.current_user_top_artists(limit=50, time_range="long_term")["items"]
genres = Counter(g for a in top50 for g in a.get("genres", []))

if genres:
    top_genres = pd.Series(dict(genres.most_common(15))).sort_values()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top_genres.index, top_genres.values)
    ax.set_title("Most common genres among your top 50 artists")
    ax.set_xlabel("Number of artists")
    fig.tight_layout()
    fig.savefig("genres.png", dpi=150)
else:
    print("\nNo genre data returned by the API.")

# --- 3. Recently played: save to a growing history file --------------------
# The API only returns the last 50 plays. Running this script regularly and
# appending to a CSV builds up your own listening history over time.
os.makedirs("data", exist_ok=True)
history_file = "data/recent_plays.csv"

items = sp.current_user_recently_played(limit=50)["items"]
recent = pd.DataFrame([{
    "played_at": it["played_at"],
    "track": it["track"]["name"],
    "artist": it["track"]["artists"][0]["name"],
    "album": it["track"]["album"]["name"],
    "duration_ms": it["track"]["duration_ms"],
    "track_uri": it["track"]["uri"],
} for it in items])

if os.path.exists(history_file):
    recent = pd.concat([pd.read_csv(history_file), recent], ignore_index=True)

recent = recent.drop_duplicates(subset=["played_at", "track_uri"]).sort_values("played_at")
recent.to_csv(history_file, index=False)
print(f"\n{len(recent)} plays saved in {history_file}")

# --- 4. Chart: recent plays by hour of day ---------------------------------
recent["played_at"] = pd.to_datetime(recent["played_at"], utc=True, format="ISO8601").dt.tz_convert("Europe/Oslo")
by_hour = recent.groupby(recent["played_at"].dt.hour).size().reindex(range(24), fill_value=0)

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(by_hour.index, by_hour.values)
ax.set_title("Recent plays by hour of day")
ax.set_xlabel("Hour")
ax.set_ylabel("Plays")
ax.set_xticks(range(24))
fig.tight_layout()
fig.savefig("recent_by_hour.png", dpi=150)

plt.show()