"""
Spotify API integration module.

Uses the Spotify API to fetch currently playing or recently played tracks.
Requires environment variables:
    - SPOTIFY_CLIENT_ID: Your Spotify application client ID
    - SPOTIFY_SECRET_ID: Your Spotify application client secret
    - SPOTIFY_REFRESH_TOKEN: OAuth refresh token for the user
"""

from __future__ import annotations

import random
import threading
from base64 import b64encode
from dataclasses import dataclass
from typing import Any, Optional

import requests

from .config import spotify_config
from .exceptions import APIError, AuthenticationError, NoTracksError


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
    track_id: str = ""


@dataclass
class AudioFeatures:
    """Audio features for a track from Spotify's audio analysis."""

    tempo: float  # BPM (beats per minute)
    energy: float  # 0.0 to 1.0 - intensity and activity
    danceability: float  # 0.0 to 1.0 - how suitable for dancing
    valence: float  # 0.0 to 1.0 - musical positivity/happiness
    loudness: float  # dB - overall loudness

    @property
    def beat_duration_ms(self) -> int:
        """Calculate duration of one beat in milliseconds."""
        if self.tempo <= 0:
            return 500  # Default to 120 BPM
        return int(60000 / self.tempo)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template use."""
        return {
            "tempo": self.tempo,
            "energy": self.energy,
            "danceability": self.danceability,
            "valence": self.valence,
            "loudness": self.loudness,
            "beat_duration_ms": self.beat_duration_ms,
        }


class SpotifyTokenManager:
    """
    Thread-safe token manager for Spotify API authentication.
    
    Handles token refresh automatically when tokens expire.
    """

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._lock = threading.Lock()

    def _get_auth_header(self) -> str:
        """Get base64 encoded authorization header."""
        credentials = f"{spotify_config.client_id}:{spotify_config.client_secret}"
        return b64encode(credentials.encode()).decode("ascii")

    def _refresh_token(self) -> str:
        """
        Refresh the Spotify access token.
        
        Returns:
            The new access token
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": spotify_config.refresh_token,
        }
        headers = {"Authorization": f"Basic {self._get_auth_header()}"}

        try:
            response = requests.post(
                spotify_config.token_url,
                data=data,
                headers=headers,
                timeout=10,
                verify=False,
            )
            response.raise_for_status()
            result = response.json()

            if "access_token" not in result:
                raise AuthenticationError("Spotify", "No access token in response")

            return result["access_token"]

        except requests.RequestException as e:
            raise AuthenticationError("Spotify", str(e)) from e

    def get_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            force_refresh: Force a token refresh even if one exists
            
        Returns:
            Valid access token
        """
        with self._lock:
            if self._token is None or force_refresh:
                self._token = self._refresh_token()
            return self._token

    def invalidate(self) -> None:
        """Invalidate the current token, forcing refresh on next use."""
        with self._lock:
            self._token = None


# Global token manager instance
_token_manager = SpotifyTokenManager()


def is_configured() -> bool:
    """
    Check if Spotify environment variables are properly configured.
    
    Returns:
        True if all required variables are set, False otherwise
    """
    return spotify_config.is_configured()


def _api_get(url: str, retry_on_auth_error: bool = True) -> dict[str, Any]:
    """
    Make an authenticated GET request to the Spotify API.
    
    Args:
        url: The API endpoint URL
        retry_on_auth_error: Whether to retry with fresh token on 401
        
    Returns:
        JSON response as dictionary
        
    Raises:
        APIError: If the request fails
        AuthenticationError: If authentication fails after retry
    """
    token = _token_manager.get_token()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)

        if response.status_code == 401 and retry_on_auth_error:
            # Token expired, refresh and retry once
            _token_manager.invalidate()
            return _api_get(url, retry_on_auth_error=False)

        if response.status_code == 204:
            raise NoTracksError("Spotify")

        if not response.ok:
            raise APIError("Spotify", response.status_code, response.text)

        return response.json()

    except requests.RequestException as e:
        raise APIError("Spotify", 0, str(e)) from e


def get_recent_tracks(limit: int = 10) -> dict[str, Any]:
    """
    Fetch recent tracks from Spotify.
    
    Args:
        limit: Number of recent tracks to fetch (default 10, max 50)
    
    Returns:
        The API response containing recent tracks
        
    Raises:
        APIError: If the request fails
    """
    limit = min(max(1, limit), 50)  # Clamp to valid range
    url = f"{spotify_config.recently_played_url}?limit={limit}"
    return _api_get(url)


def get_audio_features(track_id: str) -> Optional[AudioFeatures]:
    """
    Fetch audio features for a track from Spotify.
    
    Args:
        track_id: Spotify track ID
        
    Returns:
        AudioFeatures object with tempo, energy, etc., or None if unavailable
    """
    if not track_id:
        return None

    try:
        url = f"https://api.spotify.com/v1/audio-features/{track_id}"
        data = _api_get(url)

        if not data:
            return None

        return AudioFeatures(
            tempo=data.get("tempo", 120.0),
            energy=data.get("energy", 0.5),
            danceability=data.get("danceability", 0.5),
            valence=data.get("valence", 0.5),
            loudness=data.get("loudness", -10.0),
        )

    except (APIError, NoTracksError):
        # Audio features not available for this track
        return None


def _extract_track_info(item: dict[str, Any], is_playing: bool) -> TrackInfo:
    """
    Extract normalized track information from Spotify API response item.
    
    Args:
        item: Track item from Spotify API
        is_playing: Whether the track is currently playing
        
    Returns:
        Normalized TrackInfo object
    """
    # Extract album art URL (prefer medium size - index 1)
    album_art_url = ""
    images = item.get("album", {}).get("images", [])
    if images:
        # Prefer medium size (index 1), fall back to first available
        album_art_url = images[1]["url"] if len(images) > 1 else images[0]["url"]

    # Extract artist info (use first artist)
    artists = item.get("artists", [{}])
    first_artist = artists[0] if artists else {}

    # Extract track ID from URI or ID field
    track_id = item.get("id", "")
    if not track_id:
        uri = item.get("uri", "")
        if uri.startswith("spotify:track:"):
            track_id = uri.split(":")[-1]

    return TrackInfo(
        is_playing=is_playing,
        track_name=item.get("name", "Unknown Track"),
        artist_name=first_artist.get("name", "Unknown Artist"),
        album_name=item.get("album", {}).get("name", "Unknown Album"),
        album_art_url=album_art_url,
        track_url=item.get("external_urls", {}).get("spotify", ""),
        artist_url=first_artist.get("external_urls", {}).get("spotify", ""),
        track_id=track_id,
    )


def get_now_playing() -> dict[str, Any]:
    """
    Get the currently playing or most recently played track from Spotify.
    
    Returns:
        A normalized track object with the following structure:
            - is_playing: bool - Whether the track is currently playing
            - track_name: str - Name of the track
            - artist_name: str - Name of the artist
            - album_name: str - Name of the album
            - album_art_url: str - URL to the album art
            - track_url: str - URL to the track on Spotify
            - artist_url: str - URL to the artist on Spotify
            - audio_features: dict or None - Audio features (tempo, energy, etc.)
    
    Raises:
        NoTracksError: If no tracks are available
        APIError: If the API request fails
    """
    is_playing = False
    item: Optional[dict[str, Any]] = None

    # Try to get currently playing track
    try:
        data = _api_get(spotify_config.now_playing_url)
        if data and "item" in data:
            is_playing = data.get("is_playing", False)
            item = data["item"]
    except NoTracksError:
        pass  # Fall through to get recent tracks

    # If not currently playing, get from recently played
    if item is None:
        data = _api_get(f"{spotify_config.recently_played_url}?limit=10")
        items = data.get("items", [])

        if not items:
            raise NoTracksError("Spotify")

        # Pick a random recent track for variety
        random_index = random.randint(0, len(items) - 1)
        item = items[random_index]["track"]
        is_playing = False

    track_info = _extract_track_info(item, is_playing)

    # Fetch audio features for BPM-synced animation
    audio_features = get_audio_features(track_info.track_id)

    # Return as dictionary for compatibility with existing code
    return {
        "is_playing": track_info.is_playing,
        "track_name": track_info.track_name,
        "artist_name": track_info.artist_name,
        "album_name": track_info.album_name,
        "album_art_url": track_info.album_art_url,
        "track_url": track_info.track_url,
        "artist_url": track_info.artist_url,
        "audio_features": audio_features.to_dict() if audio_features else None,
    }
