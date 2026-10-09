"""Keep hidden specialist readers from doing work on the Atlas landing page."""
from dash.exceptions import PreventUpdate


def require_section(section, expected):
    if section != expected:
        raise PreventUpdate
