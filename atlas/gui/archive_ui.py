"""Integrated archive browsing and browser-local image investigation."""
from dash import dcc, html


def workspace():
    return html.Div(id='archive-workspace', className='archive-workspace', style={'display':'none'}, children=[
        dcc.Store(id='archive-results'), dcc.Store(id='archive-sheets'), dcc.Store(id='archive-selected'),
        dcc.Store(id='archive-image-event'),
        dcc.Store(id='archive-note-context'),
        dcc.Store(id='archive-source-mode'),
        html.Div(className='archive-heading', children=[html.H2('Read the old map'), html.P('Find a map of your town, inspect its sheets, and write down the changes you can actually see.')]),
        html.Div(className='archive-toolbar', children=[html.Button('Find maps of this town', id='archive-search', n_clicks=0), html.Span(id='archive-town')]),
        html.Small('Search sends the selected public town and state, plus ordinary network metadata, to Library of Congress. Selected map images load directly from Library of Congress in your browser.'),
        dcc.Loading(html.Div(id='archive-status', role='status', children='Choose a town, then search the Library of Congress digitized map collection.')),
        html.Div(className='archive-body', children=[
            html.Div(className='archive-catalog', children=[html.H3('Map records'), html.Div(id='archive-cards'), dcc.Dropdown(id='archive-record', placeholder='Choose a map to inspect', clearable=False,style={'display':'none'}), html.P(id='archive-sheet-status'), dcc.Dropdown(id='archive-sheet', placeholder='Choose a sheet', clearable=False)]),
            html.Div(className='archive-viewer-panel', children=[
                html.Div(className='archive-toolbar', children=[html.Button('− Zoom out', id='archive-zoom-out'), html.Button('+ Zoom in', id='archive-zoom-in'), html.Button('Fit map', id='archive-fit'), html.Button('Rotate 90°', id='archive-rotate')]),
                html.Div(id='archive-image-viewport', style={'overflow':'auto','height':'min(62vh,700px)','minHeight':'300px','background':'#ece7da','position':'relative'}, children=[html.Img(id='archive-image', src='', alt='Selected historical map. Use zoom controls and scroll to inspect details.', style={'display':'none'}),html.P('Your map will open here. Zoom in, then scroll to read street names, boundaries and the legend.', id='archive-image-empty')]),
                html.P(id='archive-image-status', role='status'),
                html.Div(id='archive-source-record'),
                html.Details(children=[html.Summary('Open your own map image'), dcc.Upload(id='archive-upload', accept='image/png,image/jpeg,image/webp', multiple=False, children=html.Button('Choose map image')), html.P('JPEG, PNG or WebP, up to 12 MB. The image stays in this browser and is never sent to the server or saved in your notebook.')]),
            ]),
        ]),
        html.Div(className='archive-observations', children=[html.H3('What does this map show?'),html.P('Compare the date and legend. Note former streets, waterways, buildings or boundaries. A missing feature can reflect map purpose or scale.'),dcc.Input(id='archive-local-title', placeholder='Local map title / date / source (if using your own image)', maxLength=240, style={'width':'100%'}), dcc.Textarea(id='archive-notes', maxLength=1500, placeholder='Visible evidence: …\nChanges compared with today: …\nUncertain or unreadable: …',style={'width':'100%','minHeight':'120px'}),html.Button('Use this map in an investigation →',id='archive-record-note',n_clicks=0),html.Div(id='archive-save-status',role='status')]),
    ])
