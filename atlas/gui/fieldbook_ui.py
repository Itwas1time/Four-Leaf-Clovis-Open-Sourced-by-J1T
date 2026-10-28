from dash import dcc, html
from atlas.gui.expert_ui import tools as expert_tools
from atlas.gui.dig_records_ui import workspace as dig_workspace, inspector as dig_inspector


def controls():
    return html.Section([
        html.Div('KEEP THE THREAD',className='atlas-lead-eyebrow'),
        html.H2('Your fieldbook.',className='atlas-brief-heading'),
        dcc.RadioItems(id='fieldbook-section', value='readings', options=[{'label':'Saved readings','value':'readings'}, {'label':'Dig records','value':'dig'}], className='clovis-library-tabs'),
        html.Div(id='workspace-autosync-status',className='atlas-help',role='status'),
        html.Button('Sync saved readings',id='workspace-sync',n_clicks=0,className='atlas-secondary-button'),
        html.P("Merge this browser's readings with readings retained by the local app. Use this to recover readings after a restore or make them available in another browser on this computer.",className='atlas-help'),
        html.Button('Download complete workspace',id='workspace-export',n_clicks=0,className='atlas-primary-button'),
        html.Button('Restore complete workspace',id='workspace-import',n_clicks=0,className='atlas-secondary-button'),
        html.P("Includes this browser's saved readings, all local dig projects, revisions and original photos. Restore merges compatible work; conflicts cancel the restore.",className='atlas-help'),
        html.Div(id='workspace-transfer-status',className='atlas-help',role='status'),
        html.Div([
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
        html.Button('Restore a fieldbook',id='fieldbook-import',n_clicks=0,className='atlas-secondary-button'),
        dcc.Store(id='fieldbook-imported'),
        dcc.Store(id='fieldbook-reconciled'),
        html.P('Notes are saved in this browser; original photos are kept by the local app. Download a backup to move devices: JSON for notes alone, ZIP when photos are attached. Restoring merges notes.',className='atlas-help'),
        html.Div(id='fieldbook-transfer-status',className='atlas-help',role='status'),
        html.Div(id='fieldbook-status',className='atlas-status-card',role='status'),
        dcc.Download(id='fieldbook-download'),
        ], id='fieldbook-reading-controls'),
        html.P('Choose or create a project in the workbench. Link field records to the units, contexts and source documents you actually observed.', id='dig-controls-help', className='atlas-help', style={'display':'none'}),
    ],id='fieldbook-controls',className='atlas-resident-controls',style={'display':'none'})


def workspace():
    return html.Section([
        html.Div([
        html.Div('FOLLOW YOUR CURIOSITY',className='atlas-lead-eyebrow'),
        html.H2('Pick up where you left off.',className='atlas-brief-heading'),
        html.Div(id='fieldbook-metrics', className='clovis-fieldbook-metrics'),
        html.Div(id='fieldbook-comparison'),
        expert_tools(),
        html.Div(id='fieldbook-list',className='atlas-fieldbook-list'),
        ], id='fieldbook-reading-workspace'),
        dig_workspace(),
    ],id='fieldbook-workspace',className='atlas-inspection-workspace',style={'display':'none'})


def inspector():
    return html.Section([
        html.Div([
        html.Div('SAVED FIELD NOTES',className='atlas-lead-eyebrow'),
        html.H2(id='fieldbook-title',children='Choose an investigation.',className='atlas-brief-heading'),
        html.Button('Read full notes',id='fieldbook-read-full',n_clicks=0,disabled=True,className='atlas-primary-button',
                    **{'aria-haspopup':'dialog'}),
        html.Button('Download note text',id='fieldbook-note-download',n_clicks=0,disabled=True,className='atlas-primary-button'),
        html.Button('Print / save as PDF',id='fieldbook-print',n_clicks=0,disabled=True,className='atlas-secondary-button'),
        dcc.Store(id='fieldbook-print-status'),
        html.P('Saved notes are a snapshot. Revisit Explore a town for a fresh online lookup.',className='atlas-help'),
        html.Pre(id='fieldbook-text',className='atlas-saved-text'),
        html.Div(id='fieldbook-photos'),
        ], id='fieldbook-reading-inspector'),
        dig_inspector(),
    ],id='fieldbook-inspector',className='atlas-brief-panel',style={'display':'none'})
