"""A visual observation pad and a source-linked comparison guide."""
from dash import dcc, html
from core.find_inspection import MATERIALS, SETTINGS


def controls():
    return html.Section([
        html.Div('START WITH THE OBJECT', className='atlas-lead-eyebrow'),
        html.H2('Look a little closer.', className='atlas-brief-heading'),
        html.P('Describe what you can see. Get comparison questions and make a record you can take to an expert.', className='atlas-resident-intro'),
        html.Label('What does it seem to be made of?', htmlFor='find-material', className='atlas-small-label'),
        dcc.Dropdown(id='find-material', options=[{'label':v,'value':k} for k,v in MATERIALS.items()], value='unknown', clearable=False, className='atlas-filter-dropdown'),
        html.Label('Which features can you see?', className='atlas-small-label'),
        dcc.Checklist(id='find-features', value=[], options=[], className='atlas-find-features'),
        html.Label('Where was it observed?', htmlFor='find-setting', className='atlas-small-label'),
        dcc.Dropdown(id='find-setting', options=[{'label':v,'value':k} for k,v in SETTINGS.items()], value='unknown', clearable=False, className='atlas-filter-dropdown'),
        html.Label('Size, if known', htmlFor='find-size', className='atlas-small-label'),
        dcc.Input(id='find-size', value='', maxLength=80, placeholder='e.g. 4 cm long, 3 mm thick', className='atlas-search-input'),
        html.Label('Your observations', htmlFor='find-notes', className='atlas-small-label'),
        dcc.Textarea(id='find-notes', value='', maxLength=1500, placeholder='Color, pattern, readable markings, what is missing…', className='atlas-find-notes'),
        html.P('Keep exact locations and personal details out of shared notes.', className='atlas-help'),
    ], id='inspection-controls', className='atlas-resident-controls', style={'display':'none'})


def workspace():
    return html.Section([
        html.Div('YOUR OBSERVATION PAD', className='atlas-lead-eyebrow'),
        html.H2('Every detail helps.', className='atlas-brief-heading'),
        html.P('Use a photograph to study visible features. The guide uses your observations; it does not analyze the image.', className='atlas-resident-intro'),
        dcc.Upload(id='find-photo', accept='image/jpeg,image/png,image/webp', max_size=5_000_000,
                   children=html.Button('Add a photo',className='atlas-primary-button'), multiple=False),
        html.P('The photo stays in this browser. It is not sent to the app server or saved in the fieldbook.', id='find-photo-status', className='atlas-help', role='status'),
        html.Img(id='find-photo-preview', alt='Your find for visual observation', className='atlas-find-photo', style={'display':'none'}),
        html.Div([
            html.Div('01',className='atlas-photo-step'), html.H3('Show the whole object'), html.P('Include a ruler and both sides.'),
            html.Div('02',className='atlas-photo-step'), html.H3('Look at one detail'), html.P('A rim, seam, grain or mark can be more useful than a color.'),
            html.Div('03',className='atlas-photo-step'), html.H3('Keep the context'), html.P('Record whether it was in loose fill, on the surface or attached to rock.'),
        ], id='find-photo-help', className='atlas-photo-help'),
    ], id='inspection-workspace', className='atlas-inspection-workspace', style={'display':'none'})


def report_panel():
    return html.Section([
        html.Div('COMPARE & RECORD',className='atlas-lead-eyebrow'),
        html.H2('A better question.',className='atlas-brief-heading'),
        html.Div(id='find-status',role='status',className='atlas-status-card'),
        html.Button('Download observation notes',id='find-download-button',n_clicks=0,className='atlas-primary-button atlas-brief-download'),
        html.Button('Save to fieldbook',id='find-save',n_clicks=0,className='atlas-secondary-button'),
        html.Div(id='find-save-status',role='status',className='atlas-help'),
        dcc.Download(id='find-download'),
        dcc.Markdown(id='find-guide',className='atlas-resident-summary',link_target='_blank',dangerously_allow_html=False),
    ], id='inspection-inspector',className='atlas-brief-panel',style={'display':'none'})
