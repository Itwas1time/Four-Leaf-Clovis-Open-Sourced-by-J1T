"""Render a plain-data answer card (from core.town_cards) on any screen."""
from dash import html


def answer_card(card, link_label=None):
    parts = [html.Strong(card['title'])]
    if card.get('text'):
        parts.append(html.P(card['text']))
    if card.get('items'):
        parts.append(html.Ul([html.Li(item) for item in card['items']]))
    if card.get('note'):
        parts.append(html.Small(card['note']))
    if card.get('href'):
        # A block-level link: an inline anchor styled as a button overlapped the note above it.
        parts.append(html.A((card.get('link') or link_label) if card.get('items') else 'Find your state office →', href=card['href'],
                            target='_blank', rel='noopener noreferrer', className='atlas-secondary-button',
                            style={'display': 'block', 'marginTop': '0.6rem', 'textAlign': 'center'}))
    return html.Div(parts, className='clovis-town-catalog')


def find_here_card(card):
    """'What you might find' with one-tap starting points into Inspect a find."""
    parts = [html.Strong(card['title'])]
    for group in card['groups']:
        parts.append(html.H4(group['label'], className='clovis-find-here-label'))
        parts.append(html.P(group['text']))
        if group.get('source'):
            parts.append(html.Small(html.A(group['source']['title'], href=group['source']['url'], target='_blank',
                                           rel='noopener noreferrer')))
        parts.append(html.Div([html.Button(label, n_clicks=0, className='atlas-secondary-button clovis-find-kind',
                                           id={'type': 'find-preset', 'material': material, 'feature': feature or ''})
                               for label, material, feature in group['kinds']], className='clovis-find-kinds'))
    parts.append(html.Small(card['note']))
    return html.Div(parts, className='clovis-town-catalog clovis-find-here')
