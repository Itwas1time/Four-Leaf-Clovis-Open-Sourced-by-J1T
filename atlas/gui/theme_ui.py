"""Browser-local appearance control; no application callbacks or data stores."""
from dash import html


def theme_toggle() -> html.Button:
    """Return the native button managed by assets/theme.js."""
    return html.Button(
        "Dark", id="clovis-theme-toggle", type="button",
        className="clovis-theme-toggle", title="Switch to dark appearance",
        **{"aria-label": "Dark appearance", "aria-pressed": "false"},
    )
