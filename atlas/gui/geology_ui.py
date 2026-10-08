"""Literal Dash evidence cards and an explicitly opt-in geology layer."""
from dash import dcc, html
import dash_leaflet as dl
from atlas.gui.learning_ui import glossary, unit_words

TILE_URL = 'https://tiles.macrostrat.org/carto/{z}/{x}/{y}.png'


def make_geology_layer():
    return dl.LayerGroup(id='resident-geology-layer', children=[])


def make_geology_board():
    return html.Details(id='resident-evidence-drawer',className='clovis-evidence-drawer',children=[
        html.Summary('Read rock evidence · materials, ages & sources'),
        html.Section(className='evidence-board', children=[
        html.H3('What the rock maps show', className='clovis-evidence-heading'),
        html.Details(className='geology-controls', children=[
            html.Summary('Map overlay & sources'),
            html.P('Optional overlay: Macrostrat receives visible map tile requests and network metadata. Panning requests more tiles. No browser location is needed.'),
            dcc.Checklist(id='resident-geology-toggle', options=[{'label': 'Show regional geology overlay', 'value': 'geology'}], value=[]),
            html.Label('Overlay opacity', htmlFor='resident-geology-opacity'),
            dcc.Slider(id='resident-geology-opacity', min=0.15, max=0.85, step=0.05, value=0.5,
                       marks={0.15: 'Light', 0.5: 'Medium', 0.85: 'Strong'}),
            html.P(id='resident-geology-status', role='status'),
            html.Details([html.Summary('Map colors, coverage and sources'),
                html.P('Colors come from merged geological maps. There is no fixed local color legend here; use the unit cards and original references to interpret this town. Display priority blends map scales and does not establish survey accuracy. Zooming does not validate a property or specimen.'),
                html.A('Macrostrat tile documentation', href='https://tiles.macrostrat.org/', target='_blank', rel='noopener noreferrer'),
                html.Span(' · '), html.A('CC BY 4.0', href='https://creativecommons.org/licenses/by/4.0/', target='_blank', rel='noopener noreferrer')]),
        ]),
        html.P(id='resident-evidence-status', role='status'),
        glossary(),
        html.Div(id='resident-evidence-cards', className='evidence-grid'),
        html.Div(id='resident-evidence-detail', className='evidence-detail', **{'aria-live': 'polite'}),
        dcc.Store(id='geology-note-context', data=None, storage_type='memory'),
        html.Button('Start a rock comparison from this unit', id='geology-record-note', n_clicks=0,
                    disabled=True, className='atlas-primary-button'),
    ])])


def evidence_card(card):
    return html.Button([
        html.Span(card['kind'], className='evidence-meta'), html.Strong(card['title']),
        html.Span(card['materials']), html.Small(card['age']), html.Span('View evidence →'),
    ], id={'type': 'resident-evidence-card', 'key': card['id']}, n_clicks=0, className='evidence-card')


def evidence_detail(card):
    if card is None:
        return html.P('Select an evidence card to read its description and source.', className='evidence-empty')
    children = [html.Span(card['kind'], className='evidence-meta'), html.H3(card['title']),
                html.H4('Materials / documented examples'), html.P(card['materials']), html.H4('Mapped age'),
                html.P(card['age']), unit_words(card), html.H4('Description'), html.P(card['description'])]
    if card.get('comments'):
        children += [html.H4('Original map comments'), html.P(card['comments'])]
    children += [html.H4('Source'), html.P(card['reference'])]
    if 'map_id' in card:
        children += [html.Small(f"Macrostrat map unit {card['map_id']} · original source {card['source_id']}"),
                     html.P('Original provider text is displayed literally. Distinct maps may describe the same point differently.')]
    if card.get('url'):
        children.append(html.A('Read the reviewed guide ↗', href=card['url'], target='_blank', rel='noopener noreferrer'))
    if card.get('scope_url'):
        children.append(html.A('Read formation scope ↗', href=card['scope_url'], target='_blank', rel='noopener noreferrer'))
    children.append(html.P('Town context does not establish an object, collecting permission, or likelihood of a find.'))
    return children
