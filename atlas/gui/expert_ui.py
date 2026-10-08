"""Prepare a reviewable question and record a separately attributed response."""
from dash import dcc, html


def tools():
    return html.Section([
        html.P(id='expert-source-title', className='atlas-help'),
        html.Div(id='expert-related-records'),
        html.Details([
            html.Summary('Prepare a question about these notes'),
            html.P('Make a packet to review and download. Clovis does not send it to anyone.', className='atlas-help'),
            html.Label('What would you like to know?', htmlFor='expert-question', className='atlas-small-label'),
            dcc.Textarea(id='expert-question', value='', maxLength=1500,
                         placeholder='e.g. Which visible features would help compare this fragment?', className='atlas-find-notes'),
            html.Div([
                html.Div([html.Label('A comparison you are considering (optional)', htmlFor='expert-comparison', className='atlas-small-label'),
                          dcc.Textarea(id='expert-comparison', value='', maxLength=1500,
                                       placeholder='Keep a possible explanation separate from your observations.', className='atlas-find-notes')]),
                html.Div([html.Label('A detail you would like help with (optional)', htmlFor='expert-detail', className='atlas-small-label'),
                          dcc.Textarea(id='expert-detail', value='', maxLength=1500,
                                       placeholder='e.g. Is the seam or the mark more useful to photograph?', className='atlas-find-notes')]),
            ], className='clovis-expert-grid'),
            html.Button('Preview question packet', id='expert-prepare', n_clicks=0, className='atlas-primary-button'),
            html.Div(id='expert-question-status', role='status', className='atlas-help'),
            html.Pre(id='expert-question-preview', className='clovis-expert-preview'),
            html.Div([
                html.Button('Download question packet', id='expert-download', n_clicks=0, disabled=True, className='atlas-secondary-button'),
                html.Button('Save question to fieldbook', id='expert-save', n_clicks=0, disabled=True, className='atlas-secondary-button'),
            ], className='clovis-expert-actions'),
            dcc.Store(id='expert-question-draft'),
            dcc.Download(id='expert-download-file'),
        ], id='expert-question-panel', className='clovis-expert-disclosure'),
        html.Div(id='expert-save-status', role='status', className='atlas-help'),
        html.Details([
            html.Summary('Record a response to this question'),
            html.P('Attribute what someone told you and keep the uncertainty. Saving creates another dated entry and preserves the question.', className='atlas-help'),
            html.Label('Source or public role', htmlFor='expert-attribution', className='atlas-small-label'),
            dcc.Input(id='expert-attribution', value='', maxLength=200,
                      placeholder='e.g. Museum collections desk', className='atlas-search-input'),
            html.P('A public institution or role can provide attribution without personal contact details.', className='atlas-help'),
            html.Label('Date of the response', htmlFor='expert-response-date', className='atlas-small-label'),
            dcc.Input(id='expert-response-date', type='date', value='', className='atlas-search-input'),
            html.Label('What did the source say?', htmlFor='expert-response', className='atlas-small-label'),
            dcc.Textarea(id='expert-response', value='', maxLength=4000,
                         placeholder='Record the response, including qualifications. Clovis does not verify it.', className='atlas-find-notes'),
            html.Label('What remains uncertain? (optional)', htmlFor='expert-uncertainty', className='atlas-small-label'),
            dcc.Textarea(id='expert-uncertainty', value='', maxLength=1500,
                         placeholder='e.g. A second-side photograph or source record is still needed.', className='atlas-find-notes'),
            html.Button('Save attributed response', id='expert-response-save', n_clicks=0, className='atlas-primary-button'),
        ], id='expert-response-panel', className='clovis-expert-disclosure', style={'display':'none'}),
        html.Div(id='expert-response-status', role='status', className='atlas-help'),
    ], id='expert-tools', className='clovis-expert-tools', style={'display':'none'})
