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
