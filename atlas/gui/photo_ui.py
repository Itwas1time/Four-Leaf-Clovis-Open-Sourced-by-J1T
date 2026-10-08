"""Browser-only photo inspection controls; upload callbacks own the image source."""
from dash import html


def viewer():
    """Replace the standalone find-photo-preview image without adding callbacks."""
    return html.Div([
        html.Div([
            html.Button('Zoom in', id='find-photo-zoom-in', type='button',
                        title='Zoom in (+)', **{'aria-controls': 'find-photo-viewport'}),
            html.Button('Zoom out', id='find-photo-zoom-out', type='button',
                        title='Zoom out (-)', **{'aria-controls': 'find-photo-viewport'}),
            html.Button('Rotate 90°', id='find-photo-rotate', type='button',
                        title='Rotate clockwise (R)', **{'aria-controls': 'find-photo-viewport'}),
            html.Button('Fit photo', id='find-photo-fit', type='button',
                        title='Fit and center the photo (F or 0)', **{'aria-controls': 'find-photo-viewport'}),
        ], className='clovis-photo-toolbar', role='group', **{'aria-label': 'Photo view controls'}),
        html.Div([
            html.Img(id='find-photo-preview', alt='Your find for visual observation',
                     className='clovis-photo-image', style={'display': 'none'},
                     draggable='false'),
        ], id='find-photo-viewport', className='clovis-photo-viewport', tabIndex=0,
            role='region', **{'aria-label': 'Local photo detail viewer',
                             'aria-describedby': 'find-photo-view-help',
                             'aria-keyshortcuts': '+ - ArrowUp ArrowDown ArrowLeft ArrowRight R F 0'}),
        html.Div([
            html.Span('Drag to pan; scroll or pinch to zoom. When the photo is focused, use arrow keys, +/−, R to rotate or F to fit.',
                      id='find-photo-view-help'),
            html.Span(id='find-photo-view-status', role='status', **{'aria-live': 'polite', 'aria-atomic': 'true'}),
            html.Button('Remove photo', id='find-photo-remove', type='button',
                        className='clovis-photo-remove', disabled=True,
                        title='Clear this browser photo; your original file and observation notes remain'),
        ], className='clovis-photo-caption'),
    ], id='find-photo-viewer', className='clovis-photo-viewer', hidden=True)
