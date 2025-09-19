from io import BytesIO
import os
import json
import requests
import random

from colorthief import ColorThief
from base64 import b64encode
from dotenv import load_dotenv, find_dotenv
from flask import Flask, Response, render_template

load_dotenv(find_dotenv())

# Spotify scopes:
#   user-read-currently-playing
#   user-read-recently-played

PLACEHOLDER_IMAGE = (
    "iVBORw0KGgoAAAANSUhEUgAAA4QAAAOEBAMAAAALYOIIAAAAFVBMVEXm5ub///8AAAAxMTG+vr6RkZFfX1..."
)
PLACEHOLDER_URL = "https://source.unsplash.com/random/300x300/?music"

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
SPOTIFY_TOKEN = ""

FALLBACK_THEME = "spotify.html.j2"

REFRESH_TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
RECENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/recently-played?limit=1"

app = Flask(__name__)

def getAuth():
    return b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_SECRET_ID}".encode()).decode("ascii")

def refreshToken():
    global SPOTIFY_TOKEN
    response = requests.post(
        REFRESH_TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": SPOTIFY_REFRESH_TOKEN},
        headers={"Authorization": f"Basic {getAuth()}"},
    )
    SPOTIFY_TOKEN = response.json().get("access_token")

def fetchNowPlaying():
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    resp = requests.get(NOW_PLAYING_URL, headers=headers)

    if resp.status_code == 204 or resp.status_code > 400:
        return None
    return resp.json()

def fetchRecentlyPlayed():
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    resp = requests.get(RECENTLY_PLAYING_URL, headers=headers)
    if resp.status_code > 400:
        return None
    data = resp.json()
    if "items" in data and data["items"]:
        return data["items"][0]["track"]
    return None

@app.route("/")
def index():
    refreshToken()
    now = fetchNowPlaying()

    track = None
    if now and now.get("item"):
        track = now["item"]
    else:
        track = fetchRecentlyPlayed()

    if not track:
        # fallback when nothing available
        track = {
            "name": "Nothing playing",
            "artists": [{"name": "Spotify"}],
            "album": {"images": [{"url": PLACEHOLDER_URL}]},
        }

    image_url = track["album"]["images"][0]["url"]
    artist = ", ".join([a["name"] for a in track["artists"]])
    song = track["name"]

    return render_template(
        FALLBACK_THEME,
        image_url=image_url,
        artist=artist,
        song=song,
    )

if __name__ == "__main__":
    app.run(debug=True)
