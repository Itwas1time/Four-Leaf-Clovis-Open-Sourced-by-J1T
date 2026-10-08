"""Observation callbacks never accept a photograph as a server input."""
from dash import Input, Output, State, callback, clientside_callback, html, no_update
from core.find_inspection import FEATURES, FEATURE_QUESTIONS, GUIDES, inspect_find
from core.us_places import get_place


@callback(Output('find-town','options'), Output('find-town','value'), Output('find-town-note','children'),
          Input('resident-state','value'), Input('resident-place','value'))
def find_town_option(state, geoid):
    place = get_place(geoid, state)
    label = f"Include {place['name']}, {place['state']}" if place else 'Include a public town'
    return [{'label':label,'value':'town','disabled':place is None}], [], \
        ('Optional broad context. Check only if this town belongs with your observation.' if place else
         'Use Change town in the header to choose broad context, then return here. No town is required.')


@callback(Output('find-features','options'), Output('find-features','value'), Input('find-material','value'))
def feature_choices(material):
    guide = GUIDES.get(material) if isinstance(material,str) else None
    return ([{'label':FEATURES[f],'value':f} for f in guide['features']] if guide else []), []


@callback(Output('find-care','children'), Input('find-material','value'))
def find_care(material):
    if material != 'bone':
        return []
    return html.Div([html.Strong('Leave possible bone in place.'),
        html.P('If human remains are possible, stop disturbing the area and contact local authorities. Clovis cannot distinguish human from animal remains.')],
        className='atlas-status-card clovis-find-care')


@callback(Output('find-guide','children'), Output('find-status','children'), Output('find-download-button','disabled'), Output('find-save','disabled'),
          Output('find-next-questions','children'),
          Input('find-material','value'), Input('find-features','value'), Input('find-setting','value'),
          Input('find-size','value'), Input('find-notes','value'), Input('find-town','value'),
          Input('resident-state','value'), Input('resident-place','value'))
def render_find(material, features, setting, size, notes, town_context, state, geoid):
    try:
        report = inspect_find(material,features,setting,size or '',notes or '',
                              town_context=town_context, state=state, geoid=geoid)
    except ValueError as exc:
        return '', str(exc), True, True, []
    empty=not features and not (size or '').strip() and not (notes or '').strip() and setting=='unknown'
    prompts = [(FEATURES[feature], FEATURE_QUESTIONS[feature]) for feature in report['features']]
    if not prompts:
        prompts = [('Start with a detail', question) for question in GUIDES[material]['questions'][:2]]
    questions = [html.H3('What to look at next'), html.Div([
        html.Article([html.Small(label), html.P(question),
                      html.A('Record this detail →', href='#find-notes', className='clovis-record-detail')],
                     className='clovis-find-detail-card') for label, question in prompts
    ], className='clovis-find-question-grid')]
    return report['markdown'], ('Read the comparison guide in the center. Save your observations when ready.'
        if not empty else 'Add a feature, setting, size or note to make your first record.'), False, empty, questions


@callback(Output('find-download','data'), Input('find-download-button','n_clicks'),
          State('find-material','value'), State('find-features','value'), State('find-setting','value'),
          State('find-size','value'), State('find-notes','value'), State('find-town','value'),
          State('resident-state','value'), State('resident-place','value'), prevent_initial_call=True)
def download_find(clicks,material,features,setting,size,notes,town_context,state,geoid):
    if not clicks: return no_update
    try: report=inspect_find(material,features,setting,size or '',notes or '',
                            town_context=town_context, state=state, geoid=geoid)
    except ValueError: return no_update
    return {'content':report['markdown'],'filename':'clovis-observation-notes.md','type':'text/markdown'}


clientside_callback(
    """function(contents) {
        if (!contents) return ['', {display:'none'}, {}, 'The photo stays in this browser. It is not sent to the app server or saved in the fieldbook.'];
        if (typeof contents !== 'string' || contents.length > 6700000 || !/^data:image\\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(contents))
            return ['', {display:'none'}, {}, 'Choose a JPEG, PNG or WebP photo under 5 MB.'];
        return [contents, {display:'block'}, {display:'none'}, 'Photo selected locally. Use the viewer to inspect details.'];
    }""",
    Output('find-photo-preview','src'),Output('find-photo-preview','style'),Output('find-photo-help','style'),Output('find-photo-status','children'),
    Input('find-photo','contents'))
