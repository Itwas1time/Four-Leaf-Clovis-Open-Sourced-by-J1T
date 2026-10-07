"""
Color constants, CSS-in-Python dicts, score-to-color mapping, and theme config.
"""

# -- Color Palette --
BG_PRIMARY = "#0d1117"
BG_SECONDARY = "#161b22"
BG_PANEL = "#1c2128"
BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_DIM = "#484f58"
ACCENT = "#58a6ff"
ACCENT_DIM = "#1f6feb"

# Score heatmap stops (score -> (r, g, b))
SCORE_STOPS = [
    (0.0, (37, 99, 235)),
    (0.2, (59, 130, 246)),
    (0.5, (234, 179, 8)),
    (0.7, (249, 115, 22)),
    (1.0, (220, 38, 38)),
]

# Layer color mapping
LAYER_COLORS = {
    "hydro_proximity": "#3b82f6",
    "terrain_anomaly": "#f97316",
    "lidar_anomaly": "#22c55e",
    "crop_mark": "#eab308",
    "soil_anomaly": "#92400e",
    "shelter_probability": "#a855f7",
    "known_site_proximity": "#fbbf24",
    "oral_history_reference": "#06b6d4",
    "citizen_report_density": "#6b7280",
}

# Tile provider URLs (free, no API key)
TILE_URLS = {
    "dark": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "topographic": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    "terrain": "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
}

TILE_ATTRIBUTIONS = {
    "dark": "CartoDB",
    "satellite": "Esri",
    "topographic": "OpenTopoMap",
    "terrain": "Stadia/Stamen",
}

# Font stacks
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace"
FONT_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def score_to_color(score: float) -> str:
    """Map 0.0-1.0 score to the blue-yellow-red gradient."""
    score = max(0.0, min(1.0, score))
    for i in range(1, len(SCORE_STOPS)):
        t1, c1 = SCORE_STOPS[i - 1]
        t2, c2 = SCORE_STOPS[i]
        if score <= t2:
            t = (score - t1) / (t2 - t1) if t2 != t1 else 0
            r = int(c1[0] + t * (c2[0] - c1[0]))
            g = int(c1[1] + t * (c2[1] - c1[1]))
            b = int(c1[2] + t * (c2[2] - c1[2]))
            return f"rgb({r},{g},{b})"
    return "rgb(220,38,38)"


def score_to_hex(score: float) -> str:
    """Map 0.0-1.0 score to hex color string."""
    score = max(0.0, min(1.0, score))
    for i in range(1, len(SCORE_STOPS)):
        t1, c1 = SCORE_STOPS[i - 1]
        t2, c2 = SCORE_STOPS[i]
        if score <= t2:
            t = (score - t1) / (t2 - t1) if t2 != t1 else 0
            r = int(c1[0] + t * (c2[0] - c1[0]))
            g = int(c1[1] + t * (c2[1] - c1[1]))
            b = int(c1[2] + t * (c2[2] - c1[2]))
            return f"#{r:02x}{g:02x}{b:02x}"
    return "#dc2626"


def score_to_opacity(score: float) -> float:
    """Higher scores are more opaque."""
    return 0.3 + 0.5 * max(0.0, min(1.0, score))


# -- Reusable CSS dicts --
PANEL_STYLE = {
    "backgroundColor": BG_PANEL,
    "borderRight": f"1px solid {BORDER}",
    "color": TEXT_PRIMARY,
    "fontFamily": FONT_SANS,
    "overflowY": "auto",
    "transition": "width 200ms ease-out, opacity 200ms ease-out",
    "height": "100%",
}

HEADER_STYLE = {
    "backgroundColor": BG_SECONDARY,
    "borderBottom": f"1px solid {BORDER}",
    "color": TEXT_PRIMARY,
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "space-between",
    "padding": "0 16px",
    "height": "40px",
    "fontFamily": FONT_MONO,
    "fontSize": "13px",
    "flexShrink": "0",
}

MAP_CONTAINER_STYLE = {
    "flex": "1",
    "position": "relative",
    "display": "flex",
    "flexDirection": "column",
    "minWidth": "0",
}

SECTION_HEADER_STYLE = {
    "fontSize": "12px",
    "fontWeight": "700",
    "textTransform": "uppercase",
    "letterSpacing": "1px",
    "color": "#cbd5e1",
    "padding": "12px 14px",
    "margin": "0",
}

SLIDER_CONTAINER_STYLE = {
    "backgroundColor": BG_SECONDARY,
    "borderTop": f"1px solid {BORDER}",
    "padding": "14px 20px 16px",
    "flexShrink": "0",
}
