import glob

import matplotlib.pyplot as plt
import pandas as pd

# --- Load data -------------------------------------------------------------
# Reads both the old endsong files and the new Streaming_History_Audio files.
files = glob.glob("data/endsong_*.json") + glob.glob("data/Streaming_History_Audio_*.json")
if not files:
    raise SystemExit("No data files found in data/")

df = pd.concat([pd.read_json(f) for f in files], ignore_index=True)

# Old and new exports overlap in time, so remove duplicate plays.
df = df.drop_duplicates(subset=["ts", "spotify_track_uri"])

# Timestamps are in UTC. Convert to Norwegian time so "hour of day" is correct.
df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Europe/Oslo")

# Keep music only, and only plays of at least 30 seconds.
df = df[df["master_metadata_track_name"].notna()]
df = df[df["ms_played"] >= 30_000]

df["hours"] = df["ms_played"] / 3_600_000
df["artist"] = df["master_metadata_album_artist_name"]

print(f"{len(df)} plays from {df['ts'].min().date()} to {df['ts'].max().date()}")

# --- Chart 1: listening hours per month (line chart) -----------------------
monthly = df.set_index("ts")["hours"].resample("MS").sum()

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(monthly.index, monthly.values)
ax.set_title("Listening hours per month")
ax.set_ylabel("Hours")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("monthly_hours.png", dpi=150)

# --- Chart 2: top 10 artists by hours (horizontal bar chart) ---------------
top_artists = df.groupby("artist")["hours"].sum().nlargest(10).sort_values()

fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(top_artists.index, top_artists.values)
ax.set_title("Top 10 artists")
ax.set_xlabel("Hours")
fig.tight_layout()
fig.savefig("top_artists.png", dpi=150)

# --- Chart 3: listening by hour of day (bar chart) -------------------------
by_hour = df.groupby(df["ts"].dt.hour)["hours"].sum().reindex(range(24), fill_value=0)

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(by_hour.index, by_hour.values)
ax.set_title("Listening by hour of day")
ax.set_xlabel("Hour")
ax.set_ylabel("Hours")
ax.set_xticks(range(24))
fig.tight_layout()
fig.savefig("by_hour.png", dpi=150)

plt.show()
