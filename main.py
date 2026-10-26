import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-top-read user-read-recently-played"))

def current_n_top_tracks(n):
    for t in sp.current_user_top_tracks(limit=n, time_range="long_term")["items"]:
        print(t["name"], "-", t["artists"][0]["name"])

def current_n_top_artists(n):
    for t in sp.current_user_top_artists(limit=n, time_range="long_term")["items"]:
        print(t["name"])

current_n_top_tracks(3)

current_n_top_artists(5)