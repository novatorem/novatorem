from io import BytesIO
import os
import requests
from base64 import b64encode
from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, jsonify

# Load environment variables
load_dotenv(find_dotenv())

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

REFRESH_TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
RECENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/recently-played?limit=1"

SPOTIFY_TOKEN = None
FALLBACK_THEME = "spotify.html.j2"
PLACEHOLDER_URL = "https://source.unsplash.com/random/300x300/?music"

app = Flask(__name__)

def getAuth():
    return b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_SECRET_ID}".encode()).decode("ascii")

def refreshToken():
    global SPOTIFY_TOKEN
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN,
    }
    headers = {"Authorization": f"Basic {getAuth()}"}
    response = requests.post(REFRESH_TOKEN_URL, data=data, headers=headers)

    if response.status_code != 200:
        print("❌ Failed to refresh token:", response.text)
        return None

    tokens = response.json()
    SPOTIFY_TOKEN = tokens.get("access_token")
    print("✅ Refreshed token")
    return SPOTIFY_TOKEN

def fetchNowPlaying():
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    resp = requests.get(NOW_PLAYING_URL, headers=headers)

    print("Now Playing status:", resp.status_code)
    if resp.status_code == 204 or resp.status_code > 400:
        return None
    return resp.json()

def fetchRecentlyPlayed():
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    resp = requests.get(RECENTLY_PLAYING_URL, headers=headers)

    print("Recently Played status:", resp.status_code)
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

@app.route("/now-playing")
def now_playing():
    refreshToken()
    now = fetchNowPlaying()

    track = None
    if now and now.get("item"):
        track = now["item"]
    else:
        track = fetchRecentlyPlayed()

    if not track:
        return jsonify({
            "song": "Nothing playing",
            "artist": "Spotify",
            "image_url": PLACEHOLDER_URL,
        })

    return jsonify({
        "song": track["name"],
        "artist": ", ".join([a["name"] for a in track["artists"]]),
        "image_url": track["album"]["images"][0]["url"],
    })

@app.route("/recently-played")
def recently_played():
    refreshToken()
    track = fetchRecentlyPlayed()

    if not track:
        return jsonify({
            "song": "Nothing recently played",
            "artist": "Spotify",
            "image_url": PLACEHOLDER_URL,
        })

    return jsonify({
        "song": track["name"],
        "artist": ", ".join([a["name"] for a in track["artists"]]),
        "image_url": track["album"]["images"][0]["url"],
    })

if __name__ == "__main__":
    app.run(debug=True)
