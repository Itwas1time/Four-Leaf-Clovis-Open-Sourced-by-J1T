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
        parts.append(html.A(link_label if card.get('items') else 'Find your state office →', href=card['href'],
                            target='_blank', rel='noopener noreferrer', className='atlas-secondary-button',
                            style={'display': 'block', 'marginTop': '0.6rem', 'textAlign': 'center'}))
    return html.Div(parts, className='clovis-town-catalog')
