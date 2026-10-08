"""Sourced, offline explanations beside original geological wording."""
from dash import dcc, html
from core.geology_learning import explain_unit, search_terms

TIME_GROUPS = {
    'Phanerozoic': ('Paleozoic', 'Mesozoic', 'Cenozoic'),
    'Paleozoic': ('Cambrian', 'Ordovician', 'Silurian', 'Devonian', 'Carboniferous', 'Permian'),
    'Mesozoic': ('Triassic', 'Jurassic', 'Cretaceous'),
    'Cenozoic': ('Paleogene', 'Neogene', 'Quaternary'),
    'Carboniferous': ('Mississippian', 'Pennsylvanian'),
    'Paleogene': ('Paleocene', 'Eocene', 'Oligocene'),
    'Neogene': ('Miocene', 'Pliocene'),
    'Quaternary': ('Pleistocene', 'Holocene'),
}


def word_card(term):
    content = [html.P(term['what_it_means'])]
    if term['kind'] == 'material':
        content += [html.Strong('Look for a detail'), html.P(term['observation_question'])]
    else:
        if term.get('parent'):
            content.append(html.P(f"{term['rank'].capitalize()} within {term['parent']} time."))
        names = TIME_GROUPS.get(term.get('parent'), ())
        if term['name'] in names:
            content += [html.Small('Older → younger · order only, not duration'),
                html.Div([html.Span(name, className='is-selected' if name == term['name'] else '')
                          for name in names], className='clovis-time-order')]
    content += [html.P(term['provenance_caveat'], className='atlas-help'),
        html.Div([html.A('Source' if len(term['source_urls']) == 1 else f'Source {index+1}',
                         href=url, target='_blank', rel='noopener noreferrer')
                  for index, url in enumerate(term['source_urls'])], className='clovis-word-sources')]
    return html.Details([html.Summary(term['name']), *content], className='clovis-word-card', key=term['id'])


def unit_words(card):
    if 'map_id' not in card:
        return []
    result = explain_unit(card['materials'] + ' ' + card['description'], card['age'])
    terms = [*result['material_terms'], *result['age_terms']]
    if not terms:
        return html.P('These source words are not in the reviewed vocabulary yet. Search the rock-word guide below; the original description remains above.', className='atlas-help')
    other = [*result['unrecognized_material'], *result['unrecognized_age']]
    return html.Section([
        html.H4('Words in this source'),
        html.P('Open a word to understand it and choose a detail to observe. Word matches explain language; they do not establish what occurs here.', className='atlas-help'),
        html.Div([word_card(term) for term in terms], className='clovis-word-grid'),
        html.Details([html.Summary('Other wording remains untranslated'),
                      html.P(' · '.join(other))], className='clovis-untranslated') if other else None,
    ], className='clovis-unit-learning')


def glossary():
    return html.Details([
        html.Summary('Rock words & geological time · works offline'),
        html.P('Look up a word from a map or your notes. Definitions help you describe a material; they do not identify your object.', className='atlas-help'),
        html.Label('Search a rock word or age', htmlFor='geology-word-search', className='atlas-small-label'),
        dcc.Input(id='geology-word-search', type='search', value='', maxLength=120,
                  placeholder='Try loess, basalt or Ordovician', debounce=True, className='clovis-word-search'),
        html.Div(id='geology-word-results', **{'aria-live':'polite'}),
    ], id='geology-word-guide', className='clovis-word-guide')


def glossary_results(query):
    terms = search_terms(query, limit=8)
    if not terms:
        return html.P('No reviewed word matches. Try a single rock or age name, such as sandstone or Holocene.', className='atlas-help')
    return [html.P('Showing up to 8 reviewed words. Type a name to find others.', className='atlas-help'),
            html.Div([word_card(term) for term in terms], className='clovis-word-grid')]
