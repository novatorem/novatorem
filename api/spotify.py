from io import BytesIO
import os
import json
import random
import requests
from requests.exceptions import RequestException

from colorthief import ColorThief
from base64 import b64encode
from dotenv import load_dotenv, find_dotenv
from flask import Flask, Response, render_template, request

load_dotenv(find_dotenv())

# Spotify scopes:
#   user-read-currently-playing
#   user-read-recently-played
PLACEHOLDER_IMAGE = ""
PLACEHOLDER_URL = "https://source.unsplash.com/random/300x300/?aerial"
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
SPOTIFY_TOKEN = ""

FALLBACK_THEME = "spotify.html.j2"

REFRESH_TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
RECENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/recently-played"


app = Flask(__name__)

def getAuth():
    return b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_SECRET_ID}".encode()).decode(
        "ascii"
    )

def refreshToken():
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN,
    }

    headers = {"Authorization": "Basic {}".format(getAuth())}
    response = requests.post(
        REFRESH_TOKEN_URL, data=data, headers=headers).json()

    try:
        return response["access_token"]
    except KeyError:
        print(json.dumps(response))
        print("\n---\n")
        raise KeyError(str(response))

def get(url):
    global SPOTIFY_TOKEN

    if SPOTIFY_TOKEN == "":
        SPOTIFY_TOKEN = refreshToken()

    response = requests.get(
        url, headers={"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    )

    if response.status_code == 401:
        SPOTIFY_TOKEN = refreshToken()
        response = requests.get(
            url, headers={"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
        )
    
    # Handle the 204 "No Content" case gracefully
    if response.status_code == 204:
        return None
    elif response.status_code >= 400:
        # Handle other API errors
        print(f"API Error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    return response.json()

def barGen(barCount):
    barCSS = ""
    left = 1
    for i in range(1, barCount + 1):
        anim = random.randint(500, 1000)
        # below code generates random cubic-bezier values
        x1 = random.random()
        y1 = random.random() * 2
        x2 = random.random()
        y2 = random.random() * 2
        barCSS += (
            ".bar:nth-child({})  {{ left: {}px; animation-duration: 15s, {}ms; animation-timing-function: ease, cubic-bezier({},{},{},{}); }}".format(
                i, left, anim, x1, y1, x2, y2
            )
        )
        left += 4
    return barCSS

def gradientGen(albumArtURL, color_count):
    try:
        colortheif = ColorThief(BytesIO(requests.get(albumArtURL).content))
        palette = colortheif.get_palette(color_count)
        return palette
    except RequestException as e:
        print(f"Error fetching album art for color palette: {e}")
        # Return a fallback palette if fetching fails
        return [(24, 20, 20), (50, 40, 40), (70, 60, 60), (90, 80, 80)]

def getTemplate():
    try:
        file = open("api/templates.json", "r")
        templates = json.loads(file.read())
        return templates["templates"][templates["current-theme"]]
    except Exception as e:
        print(f"Failed to load templates.\r\n```{e}```")
        return FALLBACK_THEME

def loadImageB64(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return b64encode(response.content).decode("ascii")
    except RequestException as e:
        print(f"Error fetching image: {e}")
        return PLACEHOLDER_IMAGE

def makeSVG(data, background_color, border_color):
    barCount = 84
    barCSS = barGen(barCount)
    contentBar = ""

    item = None
    currentStatus = ""

    # Check for currently playing song
    if data and "item" in data:
        item = data["item"]
        currentStatus = "Vibing to:"
        # Set contentBar to show bars if a song is playing
        contentBar = "".join(["<div class='bar'></div>" for _ in range(barCount)])
    else:
        # If not playing, get a random recently played track
        currentStatus = "Recently played:"
        try:
            # Fetch more tracks for a better random selection
            recent_plays = get(RECENTLY_PLAYING_URL + "?limit=50")
            if recent_plays and "items" in recent_plays and recent_plays["items"]:
                
                # Create a list of unique tracks to choose from
                unique_tracks = {}
                for played_item in recent_plays["items"]:
                    track = played_item["track"]
                    # Use the track ID to ensure uniqueness
                    if track["id"] not in unique_tracks:
                        unique_tracks[track["id"]] = track
                
                # Convert the unique tracks to a list and select a random one
                if unique_tracks:
                    random_track = random.choice(list(unique_tracks.values()))
                    item = random_track
                    contentBar = "".join(["<div class='bar'></div>" for _ in range(barCount)])
                else:
                    currentStatus = "No music played recently"
                    contentBar = ""
            else:
                # No recent plays available
                currentStatus = "No music playing"
                contentBar = ""  # No bars if no music is found
        except Exception as e:
            print(f"Error fetching recently played data: {e}")
            currentStatus = "No music playing"
            contentBar = ""
            
    # Process the selected item (either currently playing or recently played)
    if item:
        if item["album"]["images"] and len(item["album"]["images"]) > 1:
            image_url = item["album"]["images"][1]["url"]
            image = loadImageB64(image_url)
            barPalette = gradientGen(image_url, 4)
            songPalette = gradientGen(image_url, 2)
        else:
            image = PLACEHOLDER_IMAGE
            barPalette = gradientGen(PLACEHOLDER_URL, 4)
            songPalette = gradientGen(PLACEHOLDER_URL, 2)
        
        artistName = item["artists"][0]["name"].replace("&", "&")
        songName = item["name"].replace("&", "&")
        songURI = item["external_urls"]["spotify"]
        artistURI = item["artists"][0]["external_urls"]["spotify"]
    else:
        # Fallback for when no music data is available at all
        image = PLACEHOLDER_IMAGE
        barPalette = gradientGen(PLACEHOLDER_URL, 4)
        songPalette = gradientGen(PLACEHOLDER_URL, 2)
        artistName = "No music playing"
        songName = "Check back later"
        songURI = "#"
        artistURI = "#"

    dataDict = {
        "contentBar": contentBar,
        "barCSS": barCSS,
        "artistName": artistName,
        "songName": songName,
        "songURI": songURI,
        "artistURI": artistURI,
        "image": image,
        "status": currentStatus,
        "background_color": background_color,
        "border_color": border_color,
        "barPalette": barPalette,
        "songPalette": songPalette
    }

    return render_template(getTemplate(), **dataDict)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@app.route('/with_parameters')
def catch_all(path):
    background_color = request.args.get('background_color') or "181414"
    border_color = request.args.get('border_color') or "181414"

    data = None
    try:
        # First, try to get the currently playing song
        data = get(NOW_PLAYING_URL)
    except Exception as e:
        print(f"Error fetching currently playing data: {e}")
    
    svg = makeSVG(data, background_color, border_color)

    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"

    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=os.getenv("PORT") or 5000)
