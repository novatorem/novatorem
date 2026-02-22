"""
Last.fm API integration module.

Uses the Last.fm API to fetch currently playing or recently played tracks.
Requires environment variables:
    - LAST_FM_API_KEY: Your Last.fm API key
    - LAST_FM_USERNAME: The Last.fm username to fetch tracks for
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests

from .config import lastfm_config
from .exceptions import APIError, NoTracksError


@dataclass
class TrackInfo:
    """Normalized track information."""

    is_playing: bool
    track_name: str
    artist_name: str
    album_name: str
    album_art_url: str
    track_url: str
    artist_url: str


# Default audio features for Last.fm (estimated averages)
DEFAULT_AUDIO_FEATURES = {
    "tempo": 120.0,  # Average pop/rock BPM
    "energy": 0.6,
    "danceability": 0.5,
    "valence": 0.5,
    "loudness": -8.0,
    "beat_duration_ms": 500,
}


def _get_spotify_data(artist_name: str, track_name: str) -> tuple[Optional[dict[str, Any]], str]:
    """
    Try to get audio features and Spotify URL by searching for the track.
    Only works if Spotify is also configured.
    
    Args:
        artist_name: Name of the artist
        track_name: Name of the track
        
    Returns:
        Tuple of (audio_features_dict, spotify_track_url)
    """
    try:
        # Import here to avoid circular imports
        from . import spotify
        
        if not spotify.is_configured():
            return None, ""
        
        # Construct fallback search URL for user redirection
        user_query = f"{artist_name} {track_name}"
        fallback_url = f"https://open.spotify.com/search/{requests.utils.quote(user_query)}"

        # Search for the track on Spotify API
        query = f"artist:{artist_name} track:{track_name}"
        search_url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1"
        
        try:
            data = spotify._api_get(search_url)
            tracks = data.get("tracks", {}).get("items", [])
            
            if not tracks:
                # Track not found via API, return search URL as fallback
                return None, fallback_url
            
            track = tracks[0]
            track_id = track.get("id", "")
            track_url = track.get("external_urls", {}).get("spotify", "")
            
            if not track_id:
                # Track found but no ID (unlikely), use URL or fallback
                return None, track_url or fallback_url
            
            # Get audio features
            audio_features = spotify.get_audio_features(track_id)
            features_dict = audio_features.to_dict() if audio_features else None
            
            return features_dict, track_url
            
        except Exception:
            # API failure, return search URL as fallback to keep user in Spotify
            return None, fallback_url
            
    except ImportError:
        pass
        
    return None, ""


def is_configured() -> bool:
    """
    Check if Last.fm environment variables are properly configured.
    
    Returns:
        True if all required variables are set, False otherwise
    """
    return lastfm_config.is_configured()


def _fetch_album_art_from_deezer(artist_name: str, track_name: str) -> str:
    """
    Try to fetch album art from Deezer API (free, no API key required).
    Tries strict search first, then relaxed search.
    
    Args:
        artist_name: Name of the artist
        track_name: Name of the track
    
    Returns:
        URL to album art, or empty string if not found
    """
    if not artist_name or not track_name:
        return ""

    try:
        # Try strict search first
        query = f'artist:"{artist_name}" track:"{track_name}"'
        params = {"q": query, "limit": 1}
        response = requests.get(
            lastfm_config.deezer_search_url,
            params=params,
            timeout=5,
            verify=False,
        )

        if response.ok:
            data = response.json()
            tracks = data.get("data", [])
            if tracks:
                cover_url = tracks[0].get("album", {}).get("cover_big")
                if cover_url:
                    return cover_url

        # If strict search fails, try relaxed search
        query = f"{artist_name} {track_name}"
        params = {"q": query, "limit": 1}
        response = requests.get(
            lastfm_config.deezer_search_url,
            params=params,
            timeout=5,
            verify=False,
        )

        if response.ok:
            data = response.json()
            tracks = data.get("data", [])
            if tracks:
                cover_url = tracks[0].get("album", {}).get("cover_big")
                if cover_url:
                    return cover_url

        return ""

    except requests.RequestException:
        return ""


def _api_get(params: dict[str, Any]) -> dict[str, Any]:
    """
    Make a GET request to the Last.fm API.
    
    Args:
        params: Query parameters for the request
        
    Returns:
        JSON response as dictionary
        
    Raises:
        APIError: If the request fails
    """
    # Add common parameters
    params = {
        **params,
        "api_key": lastfm_config.api_key,
        "format": "json",
    }

    try:
        response = requests.get(
            lastfm_config.api_url,
            params=params,
            timeout=10,
            verify=False,
        )

        if not response.ok:
            raise APIError("Last.fm", response.status_code, response.text)

        data = response.json()

        if "error" in data:
            raise APIError(
                "Last.fm",
                data.get("error", 0),
                data.get("message", "Unknown error"),
            )

        return data

    except requests.RequestException as e:
        raise APIError("Last.fm", 0, str(e)) from e


def get_recent_tracks(limit: int = 10) -> dict[str, Any]:
    """
    Fetch recent tracks from Last.fm for the configured user.
    
    Args:
        limit: Number of recent tracks to fetch (default 10)
    
    Returns:
        The API response containing recent tracks
    
    Raises:
        APIError: If the API request fails
    """
    limit = min(max(1, limit), 200)  # Clamp to valid range

    params = {
        "method": "user.getrecenttracks",
        "user": lastfm_config.username,
        "limit": limit,
        "extended": 1,
    }

    return _api_get(params)


def _extract_image_url(images: list[dict[str, str]]) -> str:
    """
    Extract the best available image URL from Last.fm image list.
    
    Args:
        images: List of image dictionaries with 'size' and '#text' keys
        
    Returns:
        Best available image URL, or empty string if none found
    """
    # Priority order for image sizes
    size_priority = ["extralarge", "large", "medium", "small"]

    for size in size_priority:
        for img in images:
            if img.get("size") == size:
                url = img.get("#text", "")
                if url:
                    return url

    # Fallback: any available image
    for img in images:
        url = img.get("#text", "")
        if url:
            return url

    return ""


def _extract_artist_name(artist_data: Any) -> str:
    """
    Extract artist name from Last.fm artist data.
    
    Last.fm can return artist as either a dict with 'name' or '#text' key,
    or sometimes as a string.
    
    Args:
        artist_data: Artist data from Last.fm API
        
    Returns:
        Artist name string
    """
    if isinstance(artist_data, str):
        return artist_data

    if isinstance(artist_data, dict):
        return artist_data.get("name") or artist_data.get("#text", "Unknown Artist")

    return "Unknown Artist"


def _extract_artist_url(artist_data: Any, artist_name: str) -> str:
    """
    Extract or construct artist URL.
    
    Args:
        artist_data: Artist data from Last.fm API
        artist_name: Artist name (used to construct URL if not provided)
        
    Returns:
        URL to the artist's Last.fm page
    """
    if isinstance(artist_data, dict):
        url = artist_data.get("url", "")
        if url:
            return url

    # Construct URL from artist name
    if artist_name:
        encoded_name = artist_name.replace(" ", "+")
        return f"https://www.last.fm/music/{encoded_name}"

    return ""


def _extract_track_info(track: dict[str, Any]) -> TrackInfo:
    """
    Extract normalized track information from Last.fm API response.
    
    Args:
        track: Track dictionary from Last.fm API
        
    Returns:
        Normalized TrackInfo object
    """
    # Check if currently playing
    is_playing = track.get("@attr", {}).get("nowplaying", "false") == "true"

    # Extract image URL
    images = track.get("image", [])
    album_art_url = _extract_image_url(images)

    # Check if the URL is Last.fm's default placeholder
    if album_art_url and lastfm_config.placeholder_hash in album_art_url:
        album_art_url = ""  # Will try Deezer fallback

    # Extract artist info
    artist_data = track.get("artist", {})
    artist_name = _extract_artist_name(artist_data)
    track_name = track.get("name", "Unknown Track")

    # Try Deezer fallback for album art if needed
    if not album_art_url and artist_name and track_name:
        album_art_url = _fetch_album_art_from_deezer(artist_name, track_name)

    return TrackInfo(
        is_playing=is_playing,
        track_name=track_name,
        artist_name=artist_name,
        album_name=track.get("album", {}).get("#text", "Unknown Album"),
        album_art_url=album_art_url,
        track_url=track.get("url", ""),
        artist_url=_extract_artist_url(artist_data, artist_name),
    )


def get_now_playing() -> dict[str, Any]:
    """
    Get the currently playing or most recently played track from Last.fm.
    
    Returns:
        A normalized track object with the following structure:
            - is_playing: bool - Whether the track is currently playing
            - track_name: str - Name of the track
            - artist_name: str - Name of the artist
            - album_name: str - Name of the album
            - album_art_url: str - URL to the album art
            - track_url: str - URL to the track on Last.fm
            - artist_url: str - URL to the artist on Last.fm
            - audio_features: dict - Audio features (from Spotify lookup or defaults)
    
    Raises:
        NoTracksError: If no tracks are available
        APIError: If the API request fails
    """
    data = get_recent_tracks(limit=1)

    tracks = data.get("recenttracks", {}).get("track", [])

    if not tracks:
        raise NoTracksError("Last.fm")

    # If only one track, it may not be in a list
    if isinstance(tracks, dict):
        tracks = [tracks]

    track = tracks[0]
    track_info = _extract_track_info(track)

    # Try to get audio features and Spotify URL
    audio_features, spotify_url = _get_spotify_data(
        track_info.artist_name, 
        track_info.track_name
    )
    
    if audio_features is None:
        audio_features = DEFAULT_AUDIO_FEATURES.copy()

    # Prefer Spotify URL for redirect if available (more reliable playback)
    final_track_url = spotify_url if spotify_url else track_info.track_url

    # Return as dictionary for compatibility with existing code
    return {
        "is_playing": track_info.is_playing,
        "track_name": track_info.track_name,
        "artist_name": track_info.artist_name,
        "album_name": track_info.album_name,
        "album_art_url": track_info.album_art_url,
        "track_url": final_track_url,
        "artist_url": track_info.artist_url,
        "audio_features": audio_features,
    }
