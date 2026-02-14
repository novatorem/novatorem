"""
Orchestrator module - handles the main Flask app, routing, and SVG generation.

Abstracts away the core functionality from the music service providers (Spotify, Last.fm).
"""

from __future__ import annotations

import colorsys
import json
import os
import random
from io import BytesIO
from typing import Any, Optional, Tuple

import requests
import urllib3
from base64 import b64encode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from colorthief import ColorThief
from flask import Flask, Response, render_template, request, redirect

from .config import (
    ColorPalette,
    compact_svg_config,
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
                response = requests.get(self.url, timeout=10, verify=False)
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


def normalize_text_palette(
    palette: ColorPalette,
    min_l: float = 0.35,
    max_l: float = 0.75,
) -> ColorPalette:
    """
    Compress the brightness range of a text colour palette.

    Clamps the HSL lightness of each colour to [min_l, max_l] while
    preserving hue and saturation, so the lightest and darkest points
    stay readable without extreme contrast.

    Args:
        palette: List of RGB tuples
        min_l: Minimum lightness (0-1)
        max_l: Maximum lightness (0-1)

    Returns:
        Adjusted palette with clamped lightness
    """
    result: ColorPalette = []
    for r, g, b in palette:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        l = max(min_l, min(max_l, l))
        rn, gn, bn = colorsys.hls_to_rgb(h, l, s)
        result.append((int(rn * 255), int(gn * 255), int(bn * 255)))
    return result


# ============================================================================
# SVG Generation
# ============================================================================


def generate_bar_css(
    bar_count: int,
    beat_duration_ms: int = 500,
    energy: float = 0.5,
    bar_palette: Optional[list] = None,
) -> str:
    """
    Generate CSS for the SVG equalizer bars animation, synced to BPM.

    Produces a ``@keyframes barcolor`` rule that cycles ``fill`` through
    the palette, plus per-bar ``.bar:nth-child(N)`` rules that stagger
    ``animation-delay`` for both the pulse and colour-wave animations.

    Args:
        bar_count: Number of equalizer bars to generate
        beat_duration_ms: Duration of one beat in milliseconds
        energy: Track energy (0-1), affects animation intensity
        bar_palette: List of RGB tuples for bar colors

    Returns:
        CSS string for barcolor keyframe and per-bar animation timing
    """
    css_rules: list[str] = []
    palette = bar_palette or svg_config.default_bar_palette

    # Build @keyframes barcolor — cycles fill through palette colours
    looped = list(palette) + [palette[0]]
    stops: list[str] = []
    for idx, (r, g, b) in enumerate(looped):
        pct = idx / (len(looped) - 1) * 100
        stops.append(f"  {pct:.0f}% {{ fill: rgb({r},{g},{b}); }}")
    css_rules.append("@keyframes barcolor {\n" + "\n".join(stops) + "\n}")

    # --- per-bar animation timing ---
    energy_factor = 0.5 + (energy * 0.5)
    wave_duration_ms = 45000  # very slow colour drift across the row

    for i in range(1, bar_count + 1):
        # Pulse timing (slight per-bar variation)
        beat_variance = random.uniform(0.9, 1.1)
        pulse_dur = int(beat_duration_ms * beat_variance * (2 - energy_factor))
        pulse_dur = max(200, min(pulse_dur, 1500))
        pulse_delay = int((i / bar_count) * beat_duration_ms * 0.5)

        # Colour-wave delay: spread one full cycle across all bars
        wave_delay = int((i - 1) / bar_count * wave_duration_ms)

        css_rules.append(
            f".bar:nth-child({i}) {{ "
            f"animation-duration: {pulse_dur}ms, {wave_duration_ms}ms; "
            f"animation-delay: -{pulse_delay}ms, -{wave_delay}ms; "
            f"}}"
        )

    return "\n".join(css_rules)


def generate_bar_svg(
    bar_count: int,
    x_start: float,
    y_bottom: float,
    area_width: float,
    bar_height: int,
    gap: int = 1,
    bar_palette: Optional[list] = None,
) -> str:
    """
    Generate SVG ``<rect>`` elements for the equalizer bars.

    Bars are placed as native SVG shapes (not foreignObject HTML) so they
    are re-rendered as vectors at every display resolution, eliminating
    scaling artefacts.  ``shape-rendering: crispEdges`` (set in the
    template CSS) snaps edges to device pixels for uniform appearance.

    Args:
        bar_count: Number of bars
        x_start: Left edge of the bar area in SVG user units
        y_bottom: Bottom edge of the bar area in SVG user units
        area_width: Total width available for bars in SVG user units
        bar_height: Height of each bar in SVG user units
        gap: Gap between bars in SVG user units
        bar_palette: RGB tuples for initial fill colours

    Returns:
        SVG markup string containing ``<rect>`` elements
    """
    palette = bar_palette or svg_config.default_bar_palette
    bar_width = (area_width - (bar_count - 1) * gap) / bar_count
    stride = bar_width + gap
    y = y_bottom - bar_height

    paths: list[str] = []
    
    # Radius for top corners
    r = 2.0
    
    for i in range(bar_count):
        x = x_start + i * stride
        
        # Clamp radius if bar is too narrow
        actual_r = min(r, bar_width / 2)
        
        # Path for top-rounded bar
        # Start bottom-left -> go up -> curve top-left -> line top -> curve top-right -> go down -> close
        d = (
            f"M {x:.2f},{y + bar_height:.2f} "  # Bottom-left (y is top, so y+height is bottom)
            f"L {x:.2f},{y + actual_r:.2f} "    # Left vertical up to start of curve
            f"Q {x:.2f},{y:.2f} {x + actual_r:.2f},{y:.2f} " # Top-left curve
            f"L {x + bar_width - actual_r:.2f},{y:.2f} "      # Top horizontal
            f"Q {x + bar_width:.2f},{y:.2f} {x + bar_width:.2f},{y + actual_r:.2f} " # Top-right curve
            f"L {x + bar_width:.2f},{y + bar_height:.2f} "    # Right vertical down
            f"Z" # Close
        )

        color = palette[i % len(palette)]
        fill = f"rgb({color[0]},{color[1]},{color[2]})"
        
        # Use shape-rendering="geometricPrecision" to help with sub-pixel aliasing (clumping)
        paths.append(
            f'<path class="bar" d="{d}" '
            f'fill="{fill}" shape-rendering="geometricPrecision" />'
        )

    return "\n".join(paths)


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


def calculate_marquee(text: str, font_size: int, container_width: int = 330) -> dict:
    """
    Calculate marquee scroll parameters if text overflows its container.

    Uses a simple continuous loop: text is duplicated and scrolls left.
    The duration is fixed per character to maintain a consistent speed.

    Args:
        text: The raw (unescaped) display text
        font_size: CSS font-size in px
        container_width: Available width in px

    Returns:
        Dict with 'enabled', and when True: 'duration' (s)
    """
    # Estimate width (avg char width ~0.6em)
    char_width = font_size * 0.6
    text_width = len(text) * char_width
    
    # 50px is the spacer width in base.html.j2
    spacer_width = 50
    
    # Enable marquee if text + spacer overflows
    if text_width + (spacer_width / 2) <= container_width:
        return {"enabled": False}
        
    # Constant speed: pixels per second
    speed_px_per_sec = 25
    
    # Distance of one loop is text_width + spacer_width
    duration = round((text_width + spacer_width) / speed_px_per_sec, 1)
    
    return {"enabled": True, "duration": max(5.0, duration)}


def make_svg(
    track_data: dict[str, Any],
    background_color: str,
    border_color: str,
    background_type: str = "color",
    show_status: bool = False,
    is_compact: bool = False,
) -> str:
    """
    Generate SVG widget from normalized track data.
    
    Args:
        track_data: Normalized track data dict
        background_color: Hex color for background (without #)
        border_color: Hex color for border (without #)
        background_type: Type of background ("color", "blur_dark", "blur_light")
        show_status: Whether to show "Vibing to:" / "Recently played:" text
        is_compact: Whether to use compact mode layout
    
    Returns:
        Rendered SVG template string
    """
    # Select configuration based on mode
    cfg = compact_svg_config if is_compact else svg_config
    
    bar_count = cfg.eq_bar_count

    # Get audio features for BPM-synced animation
    audio_features = track_data.get("audio_features") or {}
    tempo = audio_features.get("tempo", cfg.default_tempo)
    energy = audio_features.get("energy", cfg.default_energy)

    # Calculate beat duration from BPM
    beat_duration_ms = int(60000 / tempo) if tempo > 0 else 500

    # Load image and extract colors first (needed for per-bar colors)
    album_art_url = track_data.get("album_art_url", "")
    image, bar_palette, song_palette = load_image_with_fallback(album_art_url)

    # Compress brightness so the gradient stays readable and bars aren't
    # too dark or washed out
    song_palette = normalize_text_palette(song_palette)
    bar_palette = normalize_text_palette(bar_palette, min_l=0.3, max_l=0.7)

    # Generate bar CSS with audio features and per-bar colors
    bar_css = generate_bar_css(bar_count, beat_duration_ms, energy, bar_palette)

    # --- SVG bar positioning ---
    # Compute the bar area rectangle in SVG user-space coordinates.
    # x: content starts after left-padding + border + album art + gap
    bar_x_start = (
        cfg.widget_padding_left
        + cfg.widget_border_width
        + cfg.album_art_size
        + cfg.art_content_gap
    )
    bar_x_end = (
        cfg.width
        - cfg.widget_padding_right
        - cfg.widget_border_width
    )
    bar_area_width = bar_x_end - bar_x_start

    # y: the .content column (text + bars) is vertically centred in .main
    # independently of the album art.  Estimate its bottom edge.
    inner_h = (
        cfg.height
        - (cfg.widget_padding_top + cfg.widget_border_width)
        - (cfg.widget_padding_bottom + cfg.widget_border_width)
    )
    content_h = cfg.content_column_height
    
    # Align bars to bottom of album art (which is vertically centered)
    # Album art vertical center is same as container center
    # So bottom is center + half size
    center_y = (
        cfg.widget_padding_top 
        + cfg.widget_border_width 
        + inner_h / 2
    )
    
    # If we want bars aligned to bottom of art:
    bars_y_bottom = center_y + (cfg.album_art_size / 2)

    bar_max_height = int(cfg.eq_bar_max_height + energy * 8)
    bar_svg = generate_bar_svg(
        bar_count,
        bar_x_start,
        bars_y_bottom,
        bar_area_width,
        bar_max_height,
        gap=cfg.eq_bar_gap,
        bar_palette=bar_palette,
    )

    # Set status text based on playing state
    is_playing = track_data.get("is_playing", False)
    status = "Vibing to:" if is_playing else "Recently played:"

    # Calculate marquee params from raw text (before XML escaping)
    raw_song = track_data.get("track_name", "Unknown Track")
    raw_artist = track_data.get("artist_name", "Unknown Artist")
    
    # Calculate marquee with font size from config
    song_marquee = calculate_marquee(raw_song, cfg.song_font_size, container_width=bar_area_width)
    artist_marquee = calculate_marquee(raw_artist, cfg.artist_font_size, container_width=bar_area_width)

    # Escape text for XML
    artist_name = escape_xml(raw_artist)
    song_name = escape_xml(raw_song)

    # Determine background mode
    use_blur_background = background_type in ("blur_dark", "blur_light")
    blur_is_dark = background_type == "blur_dark"

    template_data = {
        # Bar animation (SVG rects + CSS)
        "bar_svg": bar_svg,
        "bar_css": bar_css,
        # Audio features for template
        "beat_duration_ms": beat_duration_ms,
        "energy": energy,
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
        "blur_amount": cfg.blur_amount,
        "blur_overlay_opacity": (
            cfg.blur_dark_opacity if blur_is_dark else cfg.blur_light_opacity
        ),
        # Status
        "status": status,
        "show_status": show_status,
        # Dimensions & layout (single source of truth from config)
        "width": cfg.width,
        "height": cfg.height,
        "album_size": cfg.album_art_size,
        "border_radius": cfg.border_radius,
        "widget_padding_top": cfg.widget_padding_top,
        "widget_padding_right": cfg.widget_padding_right,
        "widget_padding_bottom": cfg.widget_padding_bottom,
        "widget_padding_left": cfg.widget_padding_left,
        "widget_border_width": cfg.widget_border_width,
        "art_content_gap": cfg.art_content_gap,
        "eq_spacer_height": cfg.eq_spacer_height,
        "eq_spacer_margin_top": cfg.eq_spacer_margin_top,
        "artist_margin_top": cfg.artist_margin_top,
        # Font sizes
        "song_font_size": cfg.song_font_size,
        "artist_font_size": cfg.artist_font_size,
        # Marquee
        "song_marquee": song_marquee,
        "artist_marquee": artist_marquee,
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
    is_compact = request.args.get("compact", "").lower() in ("true", "1", "yes")

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

    svg = make_svg(track_data, background_color, border_color, background_type, show_status, is_compact)

    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"

    return resp


@app.route("/preview")
def preview_page() -> Response:
    """Serve the preview page for local development."""
    candidates = [
        os.path.join(os.getcwd(), "preview.html"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "preview.html",
        ),
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return Response(f.read(), mimetype="text/html")
    return Response("preview.html not found", status=404, mimetype="text/plain")


@app.route("/redirect")
def redirect_to_song() -> Response:
    """Redirect to the currently playing song."""
    # Default fallback URL (e.g., project repository)
    fallback_url = "https://github.com/novatorem/novatorem"

    try:
        service_name, service = get_active_service()
        track_data = service.get_now_playing()
        track_url = track_data.get("track_url")
        
        if track_url:
            return redirect(track_url)
    except Exception:
        # In case of any error (service not configured, API error), use fallback
        pass

    return redirect(fallback_url)


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
