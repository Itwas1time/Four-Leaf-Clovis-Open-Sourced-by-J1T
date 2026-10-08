from dash import dcc, html


def controls():
    return html.Section([
        html.Div('KEEP THE THREAD',className='atlas-lead-eyebrow'),
        html.H2('Your fieldbook.',className='atlas-brief-heading'),
        html.P('Save town reports and object observations. Return to them, compare your notes and keep a portable backup.',className='atlas-resident-intro'),
        html.Label('Read a saved investigation',htmlFor='fieldbook-selected',className='atlas-small-label'),
        dcc.Dropdown(id='fieldbook-selected',options=[],className='atlas-filter-dropdown',placeholder='Choose saved notes'),
        html.Label('Compare with',htmlFor='fieldbook-compare',className='atlas-small-label'),
        dcc.Dropdown(id='fieldbook-compare',options=[],className='atlas-filter-dropdown',placeholder='Choose a second investigation'),
        html.Label('Add a follow-up note',htmlFor='fieldbook-followup',className='atlas-small-label'),
        dcc.Textarea(id='fieldbook-followup',value='',maxLength=1500,className='atlas-find-notes',
                     placeholder='e.g. Map title, year, sheet number, source link and what it shows. Record uncertainty and keep personal details out.'),
        html.Button('Save a follow-up',id='fieldbook-followup-save',n_clicks=0,className='atlas-secondary-button'),
        html.P('Select saved notes first. A follow-up creates another dated entry and preserves the original.',className='atlas-help'),
        html.Button('Download this fieldbook',id='fieldbook-export',n_clicks=0,className='atlas-primary-button'),
        dcc.Upload(id='fieldbook-import',accept='.json,application/json',max_size=750000,
                   children=html.Button('Restore a fieldbook',className='atlas-secondary-button'),multiple=False),
        html.P('Saved in this browser on this device. Export JSON for a backup or to move devices. Restoring merges notes; it does not erase saved work.',className='atlas-help'),
        html.Div(id='fieldbook-status',className='atlas-status-card',role='status'),
        dcc.Download(id='fieldbook-download'),
    ],id='fieldbook-controls',className='atlas-resident-controls',style={'display':'none'})


def workspace():
    return html.Section([
        html.Div('FOLLOW YOUR CURIOSITY',className='atlas-lead-eyebrow'),
        html.H2('Pick up where you left off.',className='atlas-brief-heading'),
        html.Div(id='fieldbook-metrics', className='clovis-fieldbook-metrics'),
        html.Div(id='fieldbook-comparison'),
        html.Div(id='fieldbook-list',className='atlas-fieldbook-list'),
    ],id='fieldbook-workspace',className='atlas-inspection-workspace',style={'display':'none'})


def inspector():
    return html.Section([
        html.Div('SAVED FIELD NOTES',className='atlas-lead-eyebrow'),
        html.H2(id='fieldbook-title',children='Choose an investigation.',className='atlas-brief-heading'),
        html.Button('Download these notes',id='fieldbook-note-download',n_clicks=0,disabled=True,className='atlas-primary-button'),
        html.Button('Print / save as PDF',id='fieldbook-print',n_clicks=0,disabled=True,className='atlas-secondary-button'),
        dcc.Store(id='fieldbook-print-status'),
        html.P('Saved notes are a snapshot. Revisit Explore a town for a fresh online lookup.',className='atlas-help'),
        html.Pre(id='fieldbook-text',className='atlas-saved-text'),
    ],id='fieldbook-inspector',className='atlas-brief-panel',style={'display':'none'})
