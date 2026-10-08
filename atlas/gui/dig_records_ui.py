"""Forms for the local, versioned excavation notebook."""
from dash import dcc, html
from core.dig_records import KINDS, CONTEXT_TYPES, UNITS, MAX_BACKUP_ZIP_BYTES


def text_field(identifier, label, *, area=False, limit=200, placeholder=''):
    component = dcc.Textarea if area else dcc.Input
    return html.Div([html.Label(label, htmlFor=identifier, className='atlas-small-label'),
                     component(id=identifier, value='', maxLength=limit, placeholder=placeholder,
                               className='atlas-find-notes' if area else 'atlas-search-input')])


def picker(identifier, label, options=None, **kwargs):
    return html.Div([html.Label(label, htmlFor=identifier, className='atlas-small-label'),
                     dcc.Dropdown(id=identifier, options=options or [], className='atlas-filter-dropdown', **kwargs)])


def workspace():
    return html.Div([
        html.H3('Dig records'),
        html.P('Keep your project codes, contexts and bags connected. Record observations separately from interpretations; leave unobserved context and measurements unknown.', className='atlas-help'),
        picker('dig-project', 'Local project', placeholder='Choose a project', persistence=True, persistence_type='local'),
        html.Details([html.Summary('Start a project'),
                      text_field('dig-project-code', 'Project code', limit=80, placeholder='Your course or site code'),
                      text_field('dig-project-title', 'Project title', limit=200),
                      html.Button('Create project', id='dig-project-create', n_clicks=0, className='atlas-secondary-button')]),
        html.Div([
            html.Button('Download project backup', id='dig-export', n_clicks=0, className='atlas-secondary-button'),
            dcc.Upload(id='dig-import', accept='.zip,application/zip', max_size=MAX_BACKUP_ZIP_BYTES,
                       children=html.Button('Restore project backup', className='atlas-secondary-button'), multiple=False),
        ], className='clovis-note-actions'),
        html.P('Records are saved on this computer by the local Clovis app. ZIP backups contain portable JSON and every revision. Restoring merges matching histories and refuses conflicting corrections.', className='atlas-help'),
        html.Div(id='dig-status', role='status', className='atlas-status-card'),
        html.Div([html.A('Jump to saved records', href='#dig-saved-records'), html.Span(' · '),
                  html.A('Jump to recording form', href='#dig-editor')], className='atlas-help'),
        html.Div([
            html.Section([
                html.H4('Record or correct an observation'),
                html.Button('New record', id='dig-new', n_clicks=0, className='atlas-secondary-button'),
                html.P(id='dig-edit-label', className='atlas-help'),
                picker('dig-kind', 'Record type', [{'label': label, 'value': key} for key, label in KINDS.items()], value='unit', clearable=False),
                text_field('dig-code', 'Record code', limit=80, placeholder='Keep the number used on your field sheet'),
                html.Div(picker('dig-unit', 'Recorded unit / trench', placeholder='Unknown or not used'), id='dig-unit-field'),
                html.Div(picker('dig-context', 'Recorded context', placeholder='Unknown / unprovenienced'), id='dig-context-field'),
                html.Div(picker('dig-context-type', 'Context type', [{'label': value.title(), 'value': value} for value in CONTEXT_TYPES], value='unknown', clearable=False), id='dig-context-type-field'),
                text_field('dig-description', 'Observed description', area=True, limit=4000),
                text_field('dig-interpretation', 'Interpretation / uncertainty', area=True, limit=4000),
                text_field('dig-recorder', 'Recorder label', limit=120, placeholder='As required by your project'),
                text_field('dig-date', 'Observation date', limit=10, placeholder='YYYY-MM-DD, or leave unknown'),
                html.Div([
                    text_field('dig-material', 'Recorded material', limit=200),
                    html.Label('Count, if recorded', htmlFor='dig-count', className='atlas-small-label'),
                    dcc.Input(id='dig-count', type='number', min=1, max=1000000, step=1, className='atlas-search-input'),
                ], id='dig-find-fields'),
                html.Div(text_field('dig-bag', 'Bag / container identifier', limit=200), id='dig-bag-field'),
                html.Div([
                    text_field('dig-sample-type', 'Sample type', limit=200),
                    text_field('dig-method', 'Recorded sampling method', limit=200),
                ], id='dig-sample-fields'),
                html.Div([
                    text_field('dig-depth', 'Measured depth below datum', limit=40, placeholder='Preserve your recorded precision'),
                    picker('dig-depth-unit', 'Depth unit', [{'label': value, 'value': value} for value in UNITS], placeholder='Unknown'),
                    text_field('dig-datum', 'Named depth datum', limit=200, placeholder='e.g. benchmark A, as defined by your project'),
                    html.P('Depths are not converted or compared across datums. An unknown depth stays blank.', className='atlas-help'),
                ], id='dig-depth-fields'),
                html.Div([
                    text_field('dig-citation', 'Source citation / document identifier', area=True, limit=4000),
                    text_field('dig-url', 'HTTPS source link, if available', limit=2000),
                ], id='dig-source-fields'),
                picker('dig-sources', 'Supporting source documents', multi=True, value=[], placeholder='Search recorded source codes'),
                html.Button('Save record', id='dig-save', n_clicks=0, className='atlas-primary-button'),
            ], id='dig-editor', className='clovis-dig-editor'),
            html.Section([
                html.H4('Saved project records'),
                text_field('dig-query', 'Search records', limit=120),
                html.P(id='dig-record-count', className='atlas-help'),
                html.Div(id='dig-record-list'),
                html.Div([html.Button('Previous', id='dig-prev', n_clicks=0, className='atlas-secondary-button'),
                          html.Span(id='dig-page-label'),
                          html.Button('Next', id='dig-next', n_clicks=0, className='atlas-secondary-button')], className='clovis-library-pagination'),
            ], id='dig-saved-records'),
        ], className='clovis-dig-grid'),
        html.Details([
            html.Summary('Context relationships'),
            html.P('Record an observed sequence or an explicit correlation. Clovis checks circular sequences; it does not infer dates or phases.', className='atlas-help'),
            picker('dig-relation-a', 'First context', placeholder='Search a context code'),
            picker('dig-relation-kind', 'Recorded relationship', [{'label': 'is above', 'value': 'above'}, {'label': 'is below', 'value': 'below'}, {'label': 'is the same as', 'value': 'same_as'}], value='above', clearable=False),
            picker('dig-relation-b', 'Second context', placeholder='Search a context code'),
            text_field('dig-relation-note', 'Observation or reason for correction', area=True, limit=2000),
            html.Button('Save relationship', id='dig-relation-save', n_clicks=0, className='atlas-secondary-button'),
            text_field('dig-relation-query', 'Find a recorded relationship by context code or note', limit=120),
            html.Div(id='dig-relations'),
            picker('dig-relation-void-id', 'Relationship to correct', placeholder='Choose a recorded relationship'),
            html.Button('Void relationship with reason', id='dig-relation-void', n_clicks=0, className='atlas-secondary-button'),
            html.P('Voiding keeps the original observation and your dated reason in the backup.', className='atlas-help'),
        ]),
        dcc.Store(id='dig-refresh', data=0), dcc.Store(id='dig-project-request'), dcc.Store(id='dig-page', data=1),
        dcc.Store(id='dig-selection'), dcc.Store(id='dig-saved-selection'), dcc.Download(id='dig-download'),
    ], id='dig-workspace', style={'display': 'none'}, className='clovis-dig-workspace')


def inspector():
    return html.Div([html.Div('LINKED FIELD RECORD', className='atlas-lead-eyebrow'),
                     html.Div(id='dig-record-detail')], id='dig-inspector', style={'display': 'none'})
