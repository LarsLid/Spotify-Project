import glob
import os

import matplotlib.pyplot as plt
import pandas as pd
import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
load_dotenv()

EXTENDED_FILES = "data/extended/Streaming_History_Audio_*.json"
YEARS_FILE = "data/release_years.csv"
TIME_RANGES = ["short_term", "medium_term", "long_term"]
MAX_LOOKUPS = 1000  # single-track lookups per run; rerun to continue

# status_retries=0: on a rate limit, fail fast instead of sleeping for the
# Retry-After period (which can be hours), so we can save progress and stop.
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-top-read"),
                     requests_timeout=10, status_retries=0)


def load_extended_history():
    """Every music play from Spotify's extended streaming history export."""
    files = glob.glob(EXTENDED_FILES)
    if not files:
        raise SystemExit(f"No files matching {EXTENDED_FILES}")
    df = pd.concat([pd.read_json(f) for f in files], ignore_index=True)
    df = df[df["spotify_track_uri"].notna()]  # drop podcasts/audiobooks
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Europe/Oslo")
    return df.rename(columns={
        "master_metadata_track_name": "track",
        "master_metadata_album_artist_name": "artist",
        "master_metadata_album_album_name": "album",
        "spotify_track_uri": "track_uri",
    })


def load_years():
    if not os.path.exists(YEARS_FILE):
        return {}
    df = pd.read_csv(YEARS_FILE, dtype=str, keep_default_na=False)
    return dict(zip(df["track_uri"], df["release_year"]))


def save_years(years):
    pd.DataFrame(years.items(), columns=["track_uri", "release_year"]).to_csv(YEARS_FILE, index=False)


def year_of(track):
    return (track["album"].get("release_date") or "")[:4]


def fetch_years(years, plays):
    """Fill in release years for played tracks, saving progress as we go."""
    try:
        # Cheap first pass: each page of top tracks gives 50 years in one request.
        if not years:
            for time_range in TIME_RANGES:
                print(f"Fetching top tracks ({time_range})...")
                results = sp.current_user_top_tracks(limit=50, time_range=time_range)
                while results:
                    for track in results["items"]:
                        years[track["uri"]] = year_of(track)
                    results = sp.next(results) if results["next"] else None
            save_years(years)

        # Then look up the rest one by one, most-listened first.
        hours = plays.groupby("track_uri")["ms_played"].sum().sort_values(ascending=False)
        missing = [uri for uri in hours.index if uri not in years]
        todo = missing[:MAX_LOOKUPS]
        print(f"{len(missing)} songs without a release year, looking up {len(todo)}...")
        for i, uri in enumerate(todo, 1):
            years[uri] = year_of(sp.track(uri))
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}")
                save_years(years)
    except SpotifyException as e:
        if e.http_status != 429:
            raise
        retry = e.headers.get("Retry-After", "?") if e.headers else "?"
        print(f"Rate limited by Spotify (retry after {retry}s). Progress saved; rerun later.")
    finally:
        save_years(years)
    return years


plays = load_extended_history()
print(f"{len(plays)} plays of {plays['track_uri'].nunique()} songs "
      f"from {plays['ts'].min().date()} to {plays['ts'].max().date()}")

years = fetch_years(load_years(), plays)

# --- Listening time per release year (one bin per year, 1965-2025) ---------
plays["release_year"] = pd.to_numeric(plays["track_uri"].map(years), errors="coerce")
plays["hours"] = plays["ms_played"] / 3_600_000

known = plays["release_year"].notna()
print(f"Release year known for {plays.loc[known, 'hours'].sum() / plays['hours'].sum():.0%} "
      "of listening time")

in_range = plays[plays["release_year"].between(1965, 2025)]

# Hours listened per release year, indexed by year (0 for years with no plays).
hours_per_year = (in_range.groupby("release_year")["hours"].sum()
                  .reindex(range(1965, 2026), fill_value=0))
print(f"Total: {hours_per_year.sum():.0f} hours from songs released 1965-2025")
interval = (1967, 1977)
hours_in_interval = hours_per_year.loc[interval[0]:interval[1]]  # .loc includes both ends
print(f"Total: {hours_in_interval.sum():.0f} hours from songs released {interval[0]}-{interval[1]}")

fig, ax = plt.subplots(figsize=(12, 5))
colors = ["#2a78d6", "#cb0b1e"]
bars = ax.bar(hours_per_year.index, hours_per_year.values, width=0.85, color=colors[0])
for bar, year in zip(bars, hours_per_year.index):
    if interval[0] <= year <= interval[1]:
        bar.set_color(colors[1])
ax.set_title("Time listened by release year")
ax.set_xlabel("Release year")
ax.set_ylabel("Time listened (hours)")
ax.set_xlim(1964, 2026)
ax.grid(axis="y", alpha=0.3)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig("duration_by_year.png", dpi=150)
plt.show()
