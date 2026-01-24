"""
Orchestrator module - handles the main Flask app, routing, and SVG generation.

Abstracts away the core functionality from the music service providers (Spotify, Last.fm).
"""

from __future__ import annotations

import json
import os
import random
from io import BytesIO
from typing import Any, Optional, Tuple

import requests
from base64 import b64encode
from colorthief import ColorThief
from flask import Flask, Response, render_template, request

from .config import (
    ColorPalette,
    RGBColor,
    svg_config,
    template_config,
    validate_background_type,
    validate_hex_color,
)
from .exceptions import (
    ImageProcessingError,
    MusicWidgetError,
    ServiceNotConfiguredError,
)


app = Flask(__name__)


# ============================================================================
# Image Processing
# ============================================================================


class ImageData:
    """
    Container for image data and extracted color palettes.
    
    Fetches image once and caches the bytes for reuse.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._bytes: Optional[bytes] = None
        self._bar_palette: Optional[ColorPalette] = None
        self._song_palette: Optional[ColorPalette] = None

    def _fetch(self) -> bytes:
        """Fetch image bytes from URL."""
        if self._bytes is None:
            try:
                response = requests.get(self.url, timeout=10)
                response.raise_for_status()
                self._bytes = response.content
            except requests.RequestException as e:
                raise ImageProcessingError(str(e)) from e
        return self._bytes

    def get_base64(self) -> str:
        """Get image as base64 encoded string."""
        return b64encode(self._fetch()).decode("ascii")

    def get_palette(self, color_count: int) -> ColorPalette:
        """Extract color palette from image."""
        try:
            image_bytes = self._fetch()
            color_thief = ColorThief(BytesIO(image_bytes))
            return color_thief.get_palette(color_count)
        except Exception as e:
            raise ImageProcessingError(str(e)) from e

    @property
    def bar_palette(self) -> ColorPalette:
        """Get 4-color palette for equalizer bars (cached)."""
        if self._bar_palette is None:
            self._bar_palette = self.get_palette(4)
        return self._bar_palette

    @property
    def song_palette(self) -> ColorPalette:
        """Get 2-color palette for song/artist text (cached)."""
        if self._song_palette is None:
            self._song_palette = self.get_palette(2)
        return self._song_palette


def load_image_with_fallback(url: str) -> Tuple[str, ColorPalette, ColorPalette]:
    """
    Load image and extract color palettes, with fallback handling.
    
    Args:
        url: URL to the album art image
        
    Returns:
        Tuple of (base64_image, bar_palette, song_palette)
    """
    if url:
        try:
            image_data = ImageData(url)
            return (
                image_data.get_base64(),
                image_data.bar_palette,
                image_data.song_palette,
            )
        except ImageProcessingError:
            pass  # Fall through to placeholder

    # Try placeholder URL for random colors
    try:
        image_data = ImageData(svg_config.placeholder_url)
        return (
            svg_config.placeholder_image,
            image_data.bar_palette,
            image_data.song_palette,
        )
    except ImageProcessingError:
        pass  # Fall through to defaults

    # Use defaults
    return (
        svg_config.placeholder_image,
        svg_config.default_bar_palette,
        svg_config.default_song_palette,
    )


# ============================================================================
# SVG Generation
# ============================================================================


def generate_bar_css(
    bar_count: int,
    beat_duration_ms: int = 500,
    energy: float = 0.5,
    danceability: float = 0.5,
) -> str:
    """
    Generate CSS for the equalizer bars animation, synced to BPM.
    
    Args:
        bar_count: Number of equalizer bars to generate
        beat_duration_ms: Duration of one beat in milliseconds
        energy: Track energy (0-1), affects animation intensity
        danceability: Track danceability (0-1), affects animation smoothness
        
    Returns:
        CSS string for bar positioning and animation
    """
    css_rules: list[str] = []
    
    # Calculate total width and center offset
    total_width = bar_count * svg_config.bar_spacing
    container_width = 330  # max-width of content area
    start_offset = max(0, (container_width - total_width) // 2)
    left = start_offset

    # Scale animation based on energy (more energy = faster, more dramatic)
    energy_factor = 0.5 + (energy * 0.5)  # 0.5 to 1.0
    
    # Danceability affects the animation curve (more danceable = bouncier)
    bounce_factor = 0.3 + (danceability * 0.7)  # 0.3 to 1.0

    for i in range(1, bar_count + 1):
        # Base animation on beat duration with variation
        # Add slight randomness but keep it roughly on beat
        beat_variance = random.uniform(0.8, 1.2)
        anim_duration = int(beat_duration_ms * beat_variance * (2 - energy_factor))
        
        # Clamp to reasonable range
        anim_duration = max(200, min(anim_duration, 1500))

        # Create cubic-bezier based on danceability
        # Higher danceability = more bouncy (overshoot) curves
        x1 = random.uniform(0.1, 0.4)
        y1 = random.uniform(0.0, bounce_factor * 1.5)  # Overshoot based on danceability
        x2 = random.uniform(0.4, 0.8)
        y2 = random.uniform(0.8, 1.0 + bounce_factor * 0.5)

        # Add phase offset based on position (creates wave effect)
        phase_delay = int((i / bar_count) * beat_duration_ms * 0.5)

        css_rules.append(
            f".bar:nth-child({i}) {{ "
            f"left: {left}px; "
            f"animation-duration: 15s, {anim_duration}ms; "
            f"animation-delay: 0s, -{phase_delay}ms; "
            f"animation-timing-function: ease, cubic-bezier({x1:.4f},{y1:.4f},{x2:.4f},{y2:.4f}); "
            f"}}"
        )
        left += svg_config.bar_spacing

    return "\n".join(css_rules)


def generate_bar_html(bar_count: int) -> str:
    """
    Generate HTML for equalizer bars.
    
    Args:
        bar_count: Number of bars to generate
        
    Returns:
        HTML string containing bar divs
    """
    return "".join(f"<div class='bar'></div>" for _ in range(bar_count))


def get_template_name() -> str:
    """
    Get the current theme template name from configuration.
    
    Returns:
        Template filename
    """
    try:
        with open(template_config.config_path, "r", encoding="utf-8") as f:
            templates = json.load(f)
            theme = templates.get("current-theme", template_config.default_theme)
            return templates.get("templates", {}).get(theme, template_config.fallback_theme)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Failed to load templates: {e}")
        return template_config.fallback_theme


def escape_xml(text: str) -> str:
    """
    Escape special characters for XML/SVG compatibility.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for XML
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_svg(
    track_data: dict[str, Any],
    background_color: str,
    border_color: str,
    background_type: str = "color",
    show_status: bool = False,
) -> str:
    """
    Generate SVG widget from normalized track data.
    
    Args:
        track_data: Normalized track data dict with keys:
            - is_playing: bool
            - track_name: str
            - artist_name: str
            - album_art_url: str (optional)
            - track_url: str
            - artist_url: str
            - audio_features: dict (optional)
        background_color: Hex color for background (without #)
        border_color: Hex color for border (without #)
        background_type: Type of background ("color", "blur_dark", "blur_light")
        show_status: Whether to show "Vibing to:" / "Recently played:" text
    
    Returns:
        Rendered SVG template string
    """
    bar_count = svg_config.bar_count
    content_bar = generate_bar_html(bar_count)

    # Get audio features for BPM-synced animation
    audio_features = track_data.get("audio_features") or {}
    tempo = audio_features.get("tempo", svg_config.default_tempo)
    energy = audio_features.get("energy", svg_config.default_energy)
    danceability = audio_features.get("danceability", svg_config.default_danceability)

    # Calculate beat duration from BPM
    beat_duration_ms = int(60000 / tempo) if tempo > 0 else 500

    # Generate bar CSS with audio features
    bar_css = generate_bar_css(bar_count, beat_duration_ms, energy, danceability)

    # Set status text based on playing state
    is_playing = track_data.get("is_playing", False)
    status = "Vibing to:" if is_playing else "Recently played:"

    # Load image and extract colors (with caching)
    album_art_url = track_data.get("album_art_url", "")
    image, bar_palette, song_palette = load_image_with_fallback(album_art_url)

    # Escape text for XML
    artist_name = escape_xml(track_data.get("artist_name", "Unknown Artist"))
    song_name = escape_xml(track_data.get("track_name", "Unknown Track"))

    # Determine background mode
    use_blur_background = background_type in ("blur_dark", "blur_light")
    blur_is_dark = background_type == "blur_dark"

    template_data = {
        # Bar animation
        "content_bar": content_bar,
        "bar_css": bar_css,
        # Audio features for template
        "tempo": tempo,
        "beat_duration_ms": beat_duration_ms,
        "energy": energy,
        "danceability": danceability,
        # Track info
        "artist_name": artist_name,
        "song_name": song_name,
        "song_uri": track_data.get("track_url", ""),
        "artist_uri": track_data.get("artist_url", ""),
        # Image and colors
        "image": image,
        "bar_palette": bar_palette,
        "song_palette": song_palette,
        # Styling
        "background_color": background_color,
        "border_color": border_color,
        "background_type": background_type,
        "use_blur_background": use_blur_background,
        "blur_is_dark": blur_is_dark,
        "blur_amount": svg_config.blur_amount,
        "blur_overlay_opacity": (
            svg_config.blur_dark_opacity if blur_is_dark else svg_config.blur_light_opacity
        ),
        # Status
        "status": status,
        "show_status": show_status,
        # Dimensions
        "width": svg_config.width,
        "height": svg_config.height,
        "album_size": svg_config.album_art_size,
        "border_radius": svg_config.border_radius,
    }

    return render_template(get_template_name(), **template_data)


# ============================================================================
# Service Detection
# ============================================================================


def get_active_service() -> Tuple[str, Any]:
    """
    Determine which music service to use based on environment variables.
    
    Returns 'spotify' if Spotify is configured, 'lastfm' if Last.fm is configured.
    Defaults to Spotify if both are configured.
    
    Returns:
        Tuple of (service_name, service_module)
        
    Raises:
        ServiceNotConfiguredError: If no service is configured
    """
    # Import here to avoid circular imports
    from . import lastfm, spotify

    if spotify.is_configured():
        return ("spotify", spotify)
    elif lastfm.is_configured():
        return ("lastfm", lastfm)
    else:
        raise ServiceNotConfiguredError()


# ============================================================================
# Error Response Generation
# ============================================================================


def make_error_svg(message: str, status_code: int = 500) -> Response:
    """
    Generate an error SVG response.
    
    Args:
        message: Error message to display
        status_code: HTTP status code
        
    Returns:
        Flask Response with error SVG
    """
    # Simple error SVG
    error_svg = f"""<svg width="{svg_config.width}" height="{svg_config.height}" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#1a1a1a" rx="5"/>
        <text x="50%" y="50%" fill="#ff6b6b" font-family="sans-serif" font-size="14" text-anchor="middle" dominant-baseline="middle">
            {escape_xml(message)}
        </text>
    </svg>"""

    resp = Response(error_svg, mimetype="image/svg+xml", status=status_code)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# ============================================================================
# Routes
# ============================================================================


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@app.route("/with_parameters")
def catch_all(path: str) -> Response:
    """Main route handler - serves the SVG widget."""
    # Validate and sanitize color parameters
    raw_background = request.args.get("background_color", "")
    raw_border = request.args.get("border_color", "")
    raw_bg_type = request.args.get("background_type", "")

    background_color = validate_hex_color(raw_background, svg_config.default_background)
    border_color = validate_hex_color(raw_border, svg_config.default_border)
    background_type = validate_background_type(raw_bg_type, svg_config.default_background_type)

    # Optional parameters
    show_status = request.args.get("show_status", "").lower() in ("true", "1", "yes")

    try:
        service_name, service = get_active_service()
    except MusicWidgetError as e:
        return make_error_svg(e.message, e.status_code)

    try:
        track_data = service.get_now_playing()
    except MusicWidgetError as e:
        return make_error_svg(e.message, e.status_code)
    except Exception as e:
        return make_error_svg(f"Error: {str(e)}", 500)

    svg = make_svg(track_data, background_color, border_color, background_type, show_status)

    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"

    return resp


@app.route("/health")
def health_check() -> Response:
    """Health check endpoint for monitoring."""
    return Response("OK", status=200, mimetype="text/plain")


# ============================================================================
# Main Entry Point
# ============================================================================


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", debug=True, port=port)
