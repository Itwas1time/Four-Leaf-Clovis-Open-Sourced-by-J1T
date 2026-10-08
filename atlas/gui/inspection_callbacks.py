"""Observation callbacks never accept a photograph as a server input."""
from dash import Input, Output, State, callback, clientside_callback, no_update
from core.find_inspection import FEATURES, GUIDES, inspect_find


@callback(Output('find-features','options'), Output('find-features','value'), Input('find-material','value'))
def feature_choices(material):
    guide = GUIDES.get(material) if isinstance(material,str) else None
    return ([{'label':FEATURES[f],'value':f} for f in guide['features']] if guide else []), []


@callback(Output('find-guide','children'), Output('find-status','children'), Output('find-download-button','disabled'), Output('find-save','disabled'),
          Input('find-material','value'), Input('find-features','value'), Input('find-setting','value'),
          Input('find-size','value'), Input('find-notes','value'))
def render_find(material, features, setting, size, notes):
    try:
        report = inspect_find(material,features,setting,size or '',notes or '')
    except ValueError as exc:
        return '', str(exc), True, True
    empty=not features and not (size or '').strip() and not (notes or '').strip() and setting=='unknown'
    return report['markdown'], 'Describe visible features. Identity and age remain open questions.', False, empty


@callback(Output('find-download','data'), Input('find-download-button','n_clicks'),
          State('find-material','value'), State('find-features','value'), State('find-setting','value'),
          State('find-size','value'), State('find-notes','value'), prevent_initial_call=True)
def download_find(clicks,material,features,setting,size,notes):
    if not clicks: return no_update
    try: report=inspect_find(material,features,setting,size or '',notes or '')
    except ValueError: return no_update
    return {'content':report['markdown'],'filename':'clovis-observation-notes.md','type':'text/markdown'}


clientside_callback(
    """function(contents) {
        if (!contents) return ['', {display:'none'}, {}, 'The photo stays in this browser. It is not sent to the app server or saved in the fieldbook.'];
        if (typeof contents !== 'string' || contents.length > 6700000 || !/^data:image\\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(contents))
            return ['', {display:'none'}, {}, 'Choose a JPEG, PNG or WebP photo under 5 MB.'];
        return [contents, {display:'block'}, {display:'none'}, 'Photo open locally. Describe the details you can see in the controls.'];
    }""",
    Output('find-photo-preview','src'),Output('find-photo-preview','style'),Output('find-photo-help','style'),Output('find-photo-status','children'),
    Input('find-photo','contents'))
