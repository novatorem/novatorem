# Set Up Guide

## Spotify

* Create a [Spotify Application](https://developer.spotify.com/dashboard/applications)
* Take note of:
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

* Create a string combining `{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}` (e.g. `5n7o4v5a3t7o5r2e3m1:5a8n7d3r4e2w5n8o2v3a7c5`) and **encode** into [Base64](https://base64.io/).

* Then run a [curl command](https://httpie.org/run) in the form of:
```sh
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -H "Authorization: Basic {BASE64}" -d "grant_type=authorization_code&redirect_uri=http://localhost/callback/&code={CODE}" https://accounts.spotify.com/api/token
```

* Save the Refresh token

## Vercel

* Register on [Vercel](https://vercel.com/)

* Fork this repo, then create a vercel project linked to it

* Add Environment Variables:
    * `https://vercel.com/<YourName>/<ProjectName>/settings/environment-variables`
        * `SPOTIFY_REFRESH_TOKEN`
        * `SPOTIFY_CLIENT_ID`
        * `SPOTIFY_SECRET_ID`

* Deploy!

## ReadMe

You can now use the following in your readme:

```[![Spotify](https://USER_NAME.vercel.app/api/spotify)](https://open.spotify.com/user/USER_NAME)```

## Customization

If you want a distinction between the widget showing your currently playing, and your recently playing:

### Hide the EQ bar

Remove the `#` in front of `contentBar` in [line 81](https://github.com/novatorem/novatorem/blob/98ba4a8489ad86f5f73e95088e620e8859d28e71/api/spotify.py#L81) of current master, then the EQ bar will be hidden when you're in not currently playing anything.

### Status String

Have a string saying either "Vibing to:" or "Last seen playing:".

* Change [`height` to `height + 40`](https://github.com/novatorem/novatorem/blob/5194a689253ee4c89a9d365260d6050923d93dd5/api/templates/spotify.html.j2#L1-L2) (or whatever `margin-top` is set to)
* Uncomment [**.main**'s `margin-top`](https://github.com/novatorem/novatorem/blob/5194a689253ee4c89a9d365260d6050923d93dd5/api/templates/spotify.html.j2#L10)
* Uncomment [currentStatus](https://github.com/novatorem/novatorem/blob/5194a689253ee4c89a9d365260d6050923d93dd5/api/templates/spotify.html.j2#L93)

### Theme Templates

If you want to change the widget theme, you can do so by the changing the `current-theme` property in the `templates.json` file.

Themes:
* `light`
* `dark`

If you wish to customize farther, you can add your own customized `spotify.html.j2` file to the templates folder, and add the theme and file name to the `templates` dictionary in the `templates.json` file.

## Requests

Customization requests can be submitted as an issue, like https://github.com/novatorem/novatorem/issues/2

If you want to share your own customization options, open a PR if it's done or open an issue if you want it implemented by someone else.

## Debugging

If you have issues setting up, try following this [guide](https://youtu.be/n6d4KHSKqGk?t=615).

Followed the guide and still having problems?
Try checking out the functions tab in vercel, linked as:
```https://vercel.com/{name}/spotify/{build}/functions``` 

<details><summary>Which looks like-</summary>

![image](https://user-images.githubusercontent.com/16753077/91338931-b0326680-e7a3-11ea-8178-5499e0e73250.png)

</details><br>

You will see a log there, and most issues can be resolved by ensuring you have the correct variables from setup.
