{
    "name": "novatorem",
    "description": "Realtime profile Readme displaying currently playing song on Spotify using the Spotify API.",
    "scripts": {
        "postdeploy": "gunicorn --workers=1 api.spotify:app"
    },
    "env": {
        "SPOTIFY_CLIENT_ID": {
            "required": true
        },
        "SPOTIFY_REFRESH_TOKEN": {
            "required": true
        },
        "SPOTIFY_SECRET_ID": {
            "required": true
        }
    },
    "formation": {
        "web": {
            "quantity": 1
        }
    },
    "addons": [],
    "buildpacks": [
        {
            "url": "heroku/python"
        }
    ],
    "stack": "heroku-20"
}
