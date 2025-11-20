import os
from flask import Flask, request, send_file, abort
from .spotify import Spotify
from .templates import make_template

app = Flask(__name__)

@app.route("/api/view")
def view():
    uid = request.args.get("uid")
    if not uid:
        abort(400, "Missing uid parameter")

    cover_image = request.args.get("cover_image", "true") == "true"
    theme = request.args.get("theme", "default")
    show_offline = request.args.get("show_offline", "true") == "true"

    spotify = Spotify(uid=uid)
    data = spotify.get_now_playing()

    image = make_template(
        data=data,
        theme=theme,
        cover_image=cover_image,
        show_offline=show_offline
    )

    output_path = "/tmp/output.png"
    image.save(output_path)
    return send_file(output_path, mimetype="image/png")
