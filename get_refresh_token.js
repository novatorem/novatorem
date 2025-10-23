require('dotenv').config();
const express = require('express');
const request = require('request');
const querystring = require('querystring');
const app = express();

const client_id = process.env.SPOTIFY_CLIENT_ID;
const client_secret = process.env.SPOTIFY_CLIENT_SECRET;
const redirect_uri = process.env.SPOTIFY_REDIRECT_URI;

app.get('/login', (req, res) => {
  res.redirect('https://accounts.spotify.com/authorize?' +
    querystring.stringify({
      response_type: 'code',
      client_id: client_id,
      scope: 'user-read-currently-playing user-read-recently-played',
      redirect_uri: redirect_uri
    })
  );
});

app.get('/callback', (req, res) => {
  const code = req.query.code || null;
  const authOptions = {
    url: 'https://accounts.spotify.com/api/token',
    form: {
      code: code,
      redirect_uri: redirect_uri,
      grant_type: 'authorization_code'
    },
    headers: {
      'Authorization': 'Basic ' + Buffer.from(client_id + ':' + client_secret).toString('base64')
    },
    json: true
  };
  request.post(authOptions, (error, response, body) => {
    const refresh_token = body.refresh_token;
    res.send('Tu REFRESH TOKEN es:<br><br>' + refresh_token);
    console.log('REFRESH TOKEN:', refresh_token);
  });
});

app.listen(8888, () => console.log('👉 Abre en tu navegador: http://localhost:8888/login'));
