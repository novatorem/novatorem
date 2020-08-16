# Set Up Guide

## Spotify

* Create a [Spotify Application](https://developer.spotify.com/dashboard/applications)
* Put aside:
    * `Client ID`
    * `Client Secret`
* Click on **Edit Settings**
* In **Redirect URIs**:
    * Add `http://localhost/callback/`

## Refresh Token

* Navigate to the following URL:

```
https://accounts.spotify.com/authorize?client_id={SPOTIFY_CLIENT_ID}&response_type=code&scope=user-read-currently-playing,user-read-recently-played&redirect_uri=http://localhost/callback/
```

* After logging in, save the {CODE} portion of: `http://localhost/callback/?code={CODE}`

* Create a string combining `{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}` (e.g. `5n7o4v5a3t7o5r2e3m1:5a8n7d3r4e2w5n8o2v3a7c5`) and encode into [Base64](https://www.base64encode.org/).

* Then run a [curl command](https://httpie.org/run) in the form of:
```sh
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -H "Authorization: Basic {BASE64}" -d "grant_type=authorization_code&redirect_uri=http://localhost/callback/&code={CODE}" https://accounts.spotify.com/api/token
```

* Save the Refresh token

## Vercel

* Register on [Vercel](https://vercel.com/)

* Create project linked to your github repo

* Add System Variables:
    * `https://vercel.com/<YourName>/<ProjectName>/settings/environment-variables`
        * `SPOTIFY_REFRESH_TOKEN`
        * `SPOTIFY_CLIENT_ID`
        * `SPOTIFY_SECRET_ID`

* Deploy!
