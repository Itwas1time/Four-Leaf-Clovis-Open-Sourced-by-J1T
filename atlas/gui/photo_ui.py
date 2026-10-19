"""Browser-only photo inspection controls; upload callbacks own the image source."""
from urllib.parse import quote
from dash import html,dcc


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
                        n_clicks=0,title='Remove this photo from the working observation; saved notes keep their originals'),
        ], className='clovis-photo-caption'),
    ], id='find-photo-viewer', className='clovis-photo-viewer', hidden=True)


def gallery(references,*,editor=None,cache=None):
    from core.local_photos import validate_refs,PhotoStore,check_reference
    validate_refs(references)
    cache={} if cache is None else cache
    children=[]
    for row in references:
        digest=row['sha256']
        url='/clovis/photos/'+digest
        if digest not in cache:
            try:
                facts,_=PhotoStore().get(digest)
                cache[digest]=facts
            except (ValueError,OSError):cache[digest]=None
        facts=cache[digest]
        if facts is not None:check_reference(row,facts)
        photo=(html.Img(alt=row['caption'] or row['name'],key=digest,**{'data-clovis-photo-src':url}) if facts is not None else
            html.P('Original photo unavailable on this computer. Restore its photo-inclusive ZIP backup.',className='atlas-help'))
        details=[html.Strong(row['name']),html.Small(f"Original photo · {row['width']:,} × {row['height']:,} pixels")]
        if editor:
            details.extend([html.Label(['Photo caption',
                dcc.Textarea(id={'type':editor+'-photo-caption','index':digest},value=row['caption'],maxLength=1500,
                    placeholder='Side, scale, visible detail and uncertainty',className='atlas-find-notes')],className='atlas-small-label'),
                html.Button('Remove from this record',id={'type':editor+'-photo-remove','index':digest},n_clicks=0,className='atlas-secondary-button')])
            if editor=='find':
                details.append(html.Button('Inspect this photo',id={'type':'find-photo-open','index':digest},n_clicks=0,className='atlas-secondary-button'))
        elif row['caption']:details.append(html.P(row['caption']))
        if facts is not None:
            details.append(html.A('Download original',href=url+'/download?name='+quote(row['name'],safe=''),className='atlas-secondary-button'))
        children.append(html.Figure([photo,html.Figcaption(details)],className='clovis-saved-photo'))
    return children
