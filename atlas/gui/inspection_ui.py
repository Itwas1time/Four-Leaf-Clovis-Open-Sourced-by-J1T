"""A visual observation pad and a source-linked comparison guide."""
from dash import dcc, html
from core.find_inspection import MATERIALS, SETTINGS
from atlas.gui.photo_ui import viewer


def controls():
    return html.Section([
        html.Div('START WITH THE OBJECT', className='atlas-lead-eyebrow'),
        html.H2('Look a little closer.', className='atlas-brief-heading'),
        html.P('Describe what you can see. Get comparison questions and make a record you can take to an expert.', className='atlas-resident-intro'),
        html.Label('What does it seem to be made of?', htmlFor='find-material', className='atlas-small-label'),
        dcc.Dropdown(id='find-material', options=[{'label':v,'value':k} for k,v in MATERIALS.items()], value='unknown', clearable=False, className='atlas-filter-dropdown'),
        html.Div(id='find-care', role='status'),
        html.Label('Which features can you see?', className='atlas-small-label'),
        dcc.Checklist(id='find-features', value=[], options=[], className='atlas-find-features'),
        html.A('Read the questions for these features ↓', href='#find-next-questions', className='clovis-find-jump'),
        html.Label('Where was it observed?', htmlFor='find-setting', className='atlas-small-label'),
        dcc.Dropdown(id='find-setting', options=[{'label':v,'value':k} for k,v in SETTINGS.items()], value='unknown', clearable=False, className='atlas-filter-dropdown'),
        html.Label('Size, if known', htmlFor='find-size', className='atlas-small-label'),
        dcc.Input(id='find-size', value='', maxLength=80, placeholder='e.g. 4 cm long, 3 mm thick', className='atlas-search-input'),
        dcc.Checklist(id='find-town', options=[], value=[], className='atlas-find-town'),
        html.P(id='find-town-note', className='atlas-help'),
        html.Label('Your observations', htmlFor='find-notes', className='atlas-small-label'),
        dcc.Textarea(id='find-notes', value='', maxLength=1500, placeholder='Color, pattern, readable markings, what is missing…', className='atlas-find-notes'),
        html.P('Keep exact locations and personal details out of shared notes.', className='atlas-help'),
    ], id='inspection-controls', className='atlas-resident-controls', style={'display':'none'})


def workspace():
    return html.Section([
        html.Div('LOOK · COMPARE · RECORD', className='atlas-lead-eyebrow'),
        html.H2('Follow the details.', className='atlas-brief-heading'),
        html.P('Your selected features shape the questions below. A photo is optional.', className='atlas-resident-intro'),
        report_panel(),
        html.Div(id='find-next-questions', className='clovis-find-questions', **{'aria-live':'polite'}),
        html.Button('Read object guides →',id={'type':'workbench-action','target':'library','key':'object-guides'},n_clicks=0,className='atlas-secondary-button'),
        dcc.Upload(id='find-photo', accept='image/jpeg,image/png,image/webp', max_size=5_000_000,
                   children=html.Button('Add a photo',className='atlas-primary-button'), multiple=False),
        html.P('The photo stays in this browser. It is not sent to the app server or saved in the fieldbook.', id='find-photo-status', className='atlas-help', role='status'),
        viewer(),
        html.Details([
            html.Summary('How to make a useful photo record'),
            html.Div('01',className='atlas-photo-step'), html.H3('Show the whole object'), html.P('Include a ruler and both sides.'),
            html.Div('02',className='atlas-photo-step'), html.H3('Look at one detail'), html.P('A rim, seam, grain or mark can be more useful than a color.'),
            html.Div('03',className='atlas-photo-step'), html.H3('Keep the context'), html.P('Record whether it was in loose fill, on the surface or attached to rock.'),
        ], id='find-photo-help', className='atlas-photo-help'),
        html.A('Edit your observations ↑', href='#inspection-controls', className='clovis-find-jump'),
        html.Details([
            html.Summary('Read the full comparison notes & sources'),
            dcc.Markdown(id='find-guide',className='clovis-find-guide',link_target='_blank',dangerously_allow_html=False),
        ], className='clovis-find-full-guide'),
    ], id='inspection-workspace', className='atlas-inspection-workspace', style={'display':'none'})


def report_panel():
    return html.Section([
        html.Div(id='find-status',role='status',className='atlas-status-card'),
        html.Div([
            html.Button('Save to fieldbook',id='find-save',n_clicks=0,className='atlas-primary-button'),
            html.Button('Download observation notes',id='find-download-button',n_clicks=0,className='atlas-secondary-button'),
        ],className='clovis-find-record-buttons'),
        html.Div(id='find-save-status',role='status',className='atlas-help'),
        dcc.Download(id='find-download'),
        html.P('An expert can use your notes, both-side photos, scale and context. Record their response as a dated follow-up in Fieldbook.',className='atlas-help'),
    ], id='inspection-inspector',className='clovis-find-record',style={'display':'none'})
