# Set Up

This project supports two music services: **Spotify** and **Last.fm**. You only need to configure one of them.

- If **both** are configured, Spotify takes priority.
- If only **Spotify** is configured, Spotify will be used.
- If only **Last.fm** is configured, Last.fm will be used.

## Quick Start (Local Development)

1. Copy `.env.example` to `.env` and fill in your credentials for at least one service (see below):
   ```bash
   cp .env.example .env
   ```
2. Run:
   ```bash
   python start.py
   ```

That's it. The launcher will create a virtual environment, install all dependencies, start the Flask server, and open a live preview in your browser at `http://127.0.0.1:5000/preview`.

Press **Ctrl+C** to stop the server. Pass `--no-open` to skip opening the browser.

---

## Option 1: Spotify API (Recommended)

### Spotify API App

- Create a [Spotify Application](https://developer.spotify.com/dashboard/applications)
- Take note of:
  - `Client ID`
  - `Client Secret`
- Click on **Edit Settings**
- In **Redirect URIs**:
  - Add `https://example.com/callback`

## Refresh Token

### Powershell

<details>

<summary>Script to complete this section</summary>

```powershell
$ClientId = Read-Host "Client ID"
$ClientSecret = Read-Host "Client Secret"

Start-Process "https://accounts.spotify.com/authorize?client_id=$ClientId&response_type=code&scope=user-read-currently-playing,user-read-recently-played&redirect_uri=https://example.com/callback"

$Code = Read-Host "Please insert everything after 'https://example.com/callback?code='"

$ClientBytes = [System.Text.Encoding]::UTF8.GetBytes("${ClientId}:${ClientSecret}")
$EncodedClientInfo =[Convert]::ToBase64String($ClientBytes)

curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -H "Authorization: Basic $EncodedClientInfo" -d "grant_type=authorization_code&redirect_uri=https://example.com/callback&code=$Code" https://accounts.spotify.com/api/token
```

</details>

### Manual

- Navigate to the following URL:

```
https://accounts.spotify.com/authorize?client_id={SPOTIFY_CLIENT_ID}&response_type=code&scope=user-read-currently-playing,user-read-recently-played&redirect_uri=https://example.com/callback
```

- After logging in, save the {CODE} portion of: `https://example.com/callback?code={CODE}`

- Create a string combining `{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}` (e.g. `5n7o4v5a3t7o5r2e3m1:5a8n7d3r4e2w5n8o2v3a7c5`) and **encode** into [Base64](https://base64.io/).

- Then run a [curl command](https://httpie.org/run) in the form of:

```sh
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -H "Authorization: Basic {BASE64}" -d "grant_type=authorization_code&redirect_uri=https://example.com/callback&code={CODE}" https://accounts.spotify.com/api/token
```

- Save the Refresh token

---

## Option 2: Last.fm API

Last.fm is a simpler alternative that doesn't require OAuth setup. It only requires an API key and username.

### Get Last.fm API Key

1. Go to [Last.fm API Account Creation](https://www.last.fm/api/account/create)
2. Fill in the application details:
   - **Application name**: Choose any name (e.g., "Now Playing Widget")
   - **Application description**: Brief description
   - **Application homepage**: Can be your GitHub profile or repo URL
   - **Callback URL**: Leave empty or use any URL (not used for this project)
3. Click **Submit**
4. Take note of:
   - `API Key` (this becomes `LAST_FM_API_KEY`)

### Get Your Last.fm Username

Your username is the one you use to log in to Last.fm. You can find it:
- In your profile URL: `https://www.last.fm/user/{YOUR_USERNAME}`
- This becomes `LAST_FM_USERNAME`

### Environment Variables for Last.fm

You'll need these two environment variables:
- `LAST_FM_API_KEY` - Your Last.fm API key
- `LAST_FM_USERNAME` - Your Last.fm username

---

## Deployment

### Deploy to Vercel

- Register on [Vercel](https://vercel.com/)

- Fork this repo, then create a vercel project linked to it

- Add Environment Variables:

  - `https://vercel.com/<YourName>/<ProjectName>/settings/environment-variables`
  
  **For Spotify:**
    - `SPOTIFY_REFRESH_TOKEN`
    - `SPOTIFY_CLIENT_ID`
    - `SPOTIFY_SECRET_ID`
  
  **For Last.fm:**
    - `LAST_FM_API_KEY`
    - `LAST_FM_USERNAME`

- Deploy!

### Deploy to Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://dashboard.heroku.com/new?template=https%3A%2F%2Fgithub.com%2Fnovatorem%2Fnovatorem)

- Create a Heroku application via the Heroku CLI or via the Heroku Dashboard. Connect the app with your GitHub repository and enable automatic builds <br>
  `PS. automatic build means that everytime you push changes to remote, heroku will rebuild and redeploy the app.`
  - To start the Flask server execute `heroku ps:scale web=1` once the build is completed.
- Or click the `Deploy to Heroku` button above to automatically start the deployment process.

### Run locally with Docker (alternative)

If you prefer Docker over the `python start.py` launcher:

```bash
docker compose up
```

Then open [http://localhost:5000/preview](http://localhost:5000/preview). Stop with `docker compose down`.

## ReadMe

You can now use the following in your readme:

**For Spotify users:**

`[![Spotify](https://USER_NAME.vercel.app/api/orchestrator)](https://open.spotify.com/user/USER_NAME)`

**For Last.fm users:**

`[![Last.fm](https://USER_NAME.vercel.app/api/orchestrator)](https://www.last.fm/user/USER_NAME)`

## Customization

### URL Parameters

You can customize the appearance of your widget using URL query parameters:

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `background_color` | Card background color (hex, without `#`) | `181414` | `0d1117` |
| `border_color` | Card border color (hex, without `#`) | `181414` | `ffffff` |
| `background_type` | Background style: `color`, `blur_dark`, or `blur_light` | `color` | `blur_dark` |
| `show_status` | Show "Vibing to:" or "Recently played:" text | `false` | `true` |

#### Background Types

- **`color`** - Solid color background (default)
- **`blur_dark`** - Blurred album art with dark overlay (great for dark themes)
- **`blur_light`** - Blurred album art with light overlay (great for light themes)

#### Examples

Basic dark theme:
```
https://USER_NAME.vercel.app/api/orchestrator
```

Custom colors:
```
https://USER_NAME.vercel.app/api/orchestrator?background_color=0d1117&border_color=30363d
```

**Blurred album art background (dark):**
```
https://USER_NAME.vercel.app/api/orchestrator?background_type=blur_dark
```

**Blurred album art background (light):**
```
https://USER_NAME.vercel.app/api/orchestrator?background_type=blur_light
```

With status text:
```
https://USER_NAME.vercel.app/api/orchestrator?show_status=true
```

Full customization with blur:
```
https://USER_NAME.vercel.app/api/orchestrator?background_type=blur_dark&border_color=333333&show_status=true
```

### Theme Templates

Change the widget theme by editing the `current-theme` property in `api/templates.json`:

```json
{
    "current-theme": "dark",
    "templates": {
        "light": "spotify.html.j2",
        "dark": "spotify-dark.html.j2",
        "base": "base.html.j2"
    }
}
```

Available themes:
- `light` - Transparent background, no border
- `dark` - Customizable background and border colors

### Creating Custom Themes

To create your own theme:

1. Create a new template file in `api/templates/` that extends `base.html.j2`:

```jinja2
{% extends "base.html.j2" %}

{% block container_styles %}
/* Your container styles */
background-color: var(--background-color);
border: 2px solid var(--border-color);
{% endblock %}

{% block theme_styles %}
/* Your custom CSS overrides */
.song {
    font-weight: 700;
}
{% endblock %}
```

2. Add your theme to `templates.json`:

```json
{
    "current-theme": "my-theme",
    "templates": {
        "light": "spotify.html.j2",
        "dark": "spotify-dark.html.j2",
        "my-theme": "my-theme.html.j2"
    }
}
```

### Health Check Endpoint

A `/health` endpoint is available for monitoring:
```
https://USER_NAME.vercel.app/api/orchestrator/health
```

### Audio-Reactive Animations

The equalizer bars automatically sync to the music's characteristics:

**For Spotify users:**
- Bars pulse at the actual **BPM** of the song
- Animation intensity scales with the track's **energy** level
- Animation curves adjust based on **danceability**
- High-energy tracks have more dramatic bar movements and subtle album art pulsing

**For Last.fm users:**
- If you also have Spotify configured, the widget will look up the track on Spotify to get audio features
- Otherwise, sensible defaults are used (120 BPM, medium energy)

This creates a unique visual experience for each track - calm songs have gentler animations, while energetic tracks have more dynamic, punchy visuals.

## Requests

Customization requests can be submitted as an issue, like https://github.com/novatorem/novatorem/issues/2

If you want to share your own customization options, open a PR if it's done or open an issue if you want it implemented by someone else.

## Debugging

If you have issues setting up, try following this [guide](https://youtu.be/n6d4KHSKqGk?t=615).

Followed the guide and still having problems?
Try checking out the functions tab in vercel, linked as:
`https://vercel.com/{name}/spotify/{build}/functions`

<details><summary>Which looks like-</summary>

![image](https://user-images.githubusercontent.com/16753077/91338931-b0326680-e7a3-11ea-8178-5499e0e73250.png)

</details><br>

You will see a log there, and most issues can be resolved by ensuring you have the correct variables from setup.
