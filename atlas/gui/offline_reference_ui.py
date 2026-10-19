"""Read or save a reviewed source edition without leaving local evidence."""
from dash import MATCH, Input, Output, State, callback, html, no_update

from core import offline_references as references
from core.fieldbook import EMPTY_BOOK, merge_entries


def control(url, area):
    article=references.for_url(url)
    if article is None:
        return []
    key={'reference':article['id'],'area':area}
    return [html.Div([
        html.A('Read the NPS source offline',href='/reference/local/'+article['id'],
            target='_blank',rel='noopener noreferrer',className='atlas-secondary-button'),
        html.Button('Save complete source to fieldbook',
            id={'type':'offline-reference-save',**key},n_clicks=0,className='atlas-secondary-button'),
        html.P(id={'type':'offline-reference-status',**key},role='status',className='atlas-help'),
    ],className='clovis-local-source-controls')]


@callback(Output('fieldbook-store','data',allow_duplicate=True),
    Output({'type':'offline-reference-status','reference':MATCH,'area':MATCH},'children'),
    Input({'type':'offline-reference-save','reference':MATCH,'area':MATCH},'n_clicks'),
    State({'type':'offline-reference-save','reference':MATCH,'area':MATCH},'id'),
    State('fieldbook-store','data'),prevent_initial_call=True)
def save(clicks, identifier, book):
    if type(clicks) is not int or clicks<1 or not isinstance(identifier,dict):
        return no_update,no_update
    try:
        entry=references.reference_entry(identifier.get('reference'))
        return merge_entries(EMPTY_BOOK if book is None else book,[entry]),'Complete source text and edition saved to fieldbook.'
    except (ValueError,TypeError,UnicodeError) as error:
        return no_update,str(error)
