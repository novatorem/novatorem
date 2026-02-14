"""
Centralized configuration module.

Contains all constants, default values, and configuration settings.
Uses dataclasses for type safety and organization.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Tuple

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


# Type aliases
RGBColor = Tuple[int, int, int]
ColorPalette = list[RGBColor]


@dataclass(frozen=True)
class SpotifyConfig:
    """Spotify API configuration."""

    client_id: str = field(default_factory=lambda: os.getenv("SPOTIFY_CLIENT_ID", ""))
    client_secret: str = field(default_factory=lambda: os.getenv("SPOTIFY_SECRET_ID", ""))
    refresh_token: str = field(default_factory=lambda: os.getenv("SPOTIFY_REFRESH_TOKEN", ""))

    # API URLs
    token_url: str = "https://accounts.spotify.com/api/token"
    now_playing_url: str = "https://api.spotify.com/v1/me/player/currently-playing"
    recently_played_url: str = "https://api.spotify.com/v1/me/player/recently-played"

    def is_configured(self) -> bool:
        """Check if all required Spotify credentials are set."""
        return bool(self.client_id and self.client_secret and self.refresh_token)


@dataclass(frozen=True)
class LastFmConfig:
    """Last.fm API configuration."""

    api_key: str = field(default_factory=lambda: os.getenv("LAST_FM_API_KEY", ""))
    username: str = field(default_factory=lambda: os.getenv("LAST_FM_USERNAME", ""))

    # API URLs
    api_url: str = "https://ws.audioscrobbler.com/2.0/"
    deezer_search_url: str = "https://api.deezer.com/search"

    # Last.fm uses this hash for placeholder images (no real album art)
    placeholder_hash: str = "2a96cbd8b46e442fc41c2b86b821562f"

    def is_configured(self) -> bool:
        """Check if all required Last.fm credentials are set."""
        return bool(self.api_key and self.username)


# Valid background types
BACKGROUND_TYPES = frozenset({"color", "blur_dark", "blur_light"})


@dataclass(frozen=True)
class SVGConfig:
    """SVG widget configuration and defaults."""

    # Dimensions
    width: int = 540
    height: int = 135
    album_art_size: int = 121
    border_radius: int = 5

    # Widget container layout (injected into CSS via template variables)
    widget_padding_top: int = 7
    widget_padding_right: int = 8
    widget_padding_bottom: int = 7
    widget_padding_left: int = 7
    widget_border_width: int = 1
    art_content_gap: int = 7       # gap between album art and text/bars column

    # Equalizer bar area (spacer div that reserves space for SVG bar overlay)
    eq_spacer_height: int = 45
    eq_spacer_margin_top: int = 15

    # Spacing between song and artist
    artist_margin_top: int = 4

    # Equalizer bars (SVG rects)
    eq_bar_count: int = 80
    eq_bar_max_height: int = 45
    eq_bar_gap: int = 1

    # Estimated height of the content column (song + artist + eq spacer)
    # used to vertically centre the SVG bar rects.
    # song ~26 + artist_margin 4 + artist ~19 + eq_spacer_margin 6 + eq_spacer 25 = 80
    content_column_height: int = 95

    # Font sizes
    song_font_size: int = 22
    artist_font_size: int = 16

    # Default colors (hex without #)
    default_background: str = "181414"
    default_border: str = "181414"

    # Default background type: "color", "blur_dark", or "blur_light"
    default_background_type: str = "color"

    # Blur settings
    blur_amount: int = 20
    blur_dark_opacity: float = 0.7
    blur_light_opacity: float = 0.5

    # Default audio features (when not available from API)
    default_tempo: float = 120.0  # BPM
    default_energy: float = 0.6

    # Default color palettes (RGB tuples)
    default_bar_palette: ColorPalette = field(
        default_factory=lambda: [
            (75, 75, 75),
            (100, 100, 100),
            (125, 125, 125),
            (150, 150, 150),
        ]
    )
    default_song_palette: ColorPalette = field(
        default_factory=lambda: [
            (200, 200, 200),
            (150, 150, 150),
        ]
    )


@dataclass(frozen=True)
class CompactSVGConfig:
    """Configuration for compact widget mode."""

    # Dimensions
    width: int = 400
    height: int = 80
    album_art_size: int = 64
    border_radius: int = 5

    # Widget container layout
    widget_padding_top: int = 5
    widget_padding_right: int = 5
    widget_padding_bottom: int = 5
    widget_padding_left: int = 5
    widget_border_width: int = 1
    art_content_gap: int = 10

    # Equalizer bar area
    eq_spacer_height: int = 14
    eq_spacer_margin_top: int = 5

    # Spacing between song and artist
    artist_margin_top: int = -3

    # Equalizer bars
    eq_bar_count: int = 50
    eq_bar_max_height: int = 14
    eq_bar_gap: int = 1

    # Content column height (centering)
    # song ~19 + artist ~15 + margin 5 + spacer 14 = ~53
    content_column_height: int = 54

    # Font sizes
    song_font_size: int = 16
    artist_font_size: int = 13

    # Default colors (same as standard)
    default_background: str = "181414"
    default_border: str = "181414"
    default_background_type: str = "color"

    # Blur settings
    blur_amount: int = 10
    blur_dark_opacity: float = 0.7
    blur_light_opacity: float = 0.5

    # Audio features
    default_tempo: float = 120.0
    default_energy: float = 0.6

    # Palettes (same defaults)
    default_bar_palette: ColorPalette = field(
        default_factory=lambda: [
            (75, 75, 75),
            (100, 100, 100),
            (125, 125, 125),
            (150, 150, 150),
        ]
    )
    default_song_palette: ColorPalette = field(
        default_factory=lambda: [
            (200, 200, 200),
            (150, 150, 150),
        ]
    )

    # Placeholder image (base64 encoded PNG)
    placeholder_image: str = (
        "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"
    )

    # Placeholder URL for random color palettes
    placeholder_url: str = "https://picsum.photos/300/300"


@dataclass(frozen=True)
class TemplateConfig:
    """Template configuration."""

    config_path: str = "api/templates.json"
    fallback_theme: str = "base.html.j2"
    default_theme: str = "dark"


# Validation utilities
HEX_COLOR_PATTERN = re.compile(r"^[0-9a-fA-F]{6}$")


def validate_hex_color(color: str, default: str) -> str:
    """
    Validate a hex color string (without #).

    Args:
        color: The color string to validate
        default: Default color to return if validation fails

    Returns:
        Valid hex color string (6 characters, 0-9 and a-f)
    """
    if color and HEX_COLOR_PATTERN.match(color):
        return color.lower()
    return default


def validate_background_type(bg_type: str, default: str) -> str:
    """
    Validate background type parameter.

    Args:
        bg_type: The background type to validate
        default: Default type to return if validation fails

    Returns:
        Valid background type string
    """
    if bg_type and bg_type.lower() in BACKGROUND_TYPES:
        return bg_type.lower()
    return default


# Global config instances (immutable)
spotify_config = SpotifyConfig()
lastfm_config = LastFmConfig()
svg_config = SVGConfig()
compact_svg_config = CompactSVGConfig()
template_config = TemplateConfig()
