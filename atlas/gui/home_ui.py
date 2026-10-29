"""Home: three big doors and a way to wander the map (rendered from core.navigation)."""
from dash import html

from core.navigation import DOORS, SHORTCUTS


def _target(item):
    # 'town' keeps its existing id: a clientside callback opens the town chooser for it.
    if item['action'] == 'town':
        return {'id': item['key']}
    return {'id': {'type': 'workbench-action', 'target': item['action'], 'key': item['key']}}


def home_workspace():
    return html.Section([
        html.Div([
            html.P('The past of any place, free and offline.', className='clovis-home-eyebrow'),
            html.H1('What would you like to do?', className='clovis-home-title'),
        ], className='clovis-home-heading'),
        html.Div([
            html.Button([html.Strong(door['label']), html.Span(door['detail'])], n_clicks=0,
                        className='clovis-home-door', **_target(door))
            for door in DOORS
        ], className='clovis-home-doors', role='navigation', **{'aria-label': 'Starting points'}),
        html.Div([
            html.Button(item['label'], n_clicks=0, className='clovis-home-shortcut', **_target(item))
            for item in SHORTCUTS
        ], className='clovis-home-shortcuts'),
        html.P('Everything runs on this computer. Your notes stay here unless you export them.',
               className='clovis-home-note'),
    ], id='home-workspace', className='clovis-home', style={'display': 'flex'})
