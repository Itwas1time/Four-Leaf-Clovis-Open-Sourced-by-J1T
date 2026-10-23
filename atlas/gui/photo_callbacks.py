"""Photo drafts, saved galleries and local-only binary transport controls."""
import sqlite3
from dash import ALL,Input,Output,State,callback,callback_context,clientside_callback,ClientsideFunction,html,no_update
from atlas.gui.workspace_activation import when_opened
from core.local_photos import PhotoStore,validate_refs,captioned_refs
from core.dig_records import DigBook
from atlas.gui.photo_ui import gallery


for prefix,function,states in (
    ('find','chooseFindPhoto',()),
    ('dig','chooseDigPhoto',(State('dig-project','value'),State('dig-selection','data'))),
):
    clientside_callback(ClientsideFunction(namespace='clovisLocalPhotos',function_name=function),
        Output(prefix+'-photo-uploaded','data'),Input(prefix+'-photo-add','n_clicks'),*states,prevent_initial_call=True)

clientside_callback(ClientsideFunction(namespace='clovisLocalPhotos',function_name='downloadBook'),
    Output('fieldbook-transfer-status','children'),Input('fieldbook-export','n_clicks'),
    State('fieldbook-store','data'),prevent_initial_call=True)
clientside_callback(ClientsideFunction(namespace='clovisLocalPhotos',function_name='restoreBook'),
    Output('fieldbook-imported','data'),Output('fieldbook-transfer-status','children',allow_duplicate=True),
    Input('fieldbook-import','n_clicks'),State('fieldbook-store','data'),prevent_initial_call=True)
clientside_callback(ClientsideFunction(namespace='clovisLocalPhotos',function_name='downloadQuestionPhotos'),
    Output('expert-photo-download-status','children'),Input('expert-download','n_clicks'),
    State('fieldbook-store','data'),State('fieldbook-selected','value'),State('expert-question','value'),
    State('expert-comparison','value'),State('expert-detail','value'),State('expert-question-draft','data'),prevent_initial_call=True)


def update_photos(prefix,uploaded,remove_clicks,open_clicks,viewer_remove,photos,current,caption_ids,captions,owner=None):
    trigger=callback_context.triggered_id
    if isinstance(trigger,dict):
        clicks=remove_clicks if trigger.get('type')==prefix+'-photo-remove' else open_clicks
        if not any(type(n) is int and n>0 for n in clicks or []):return no_update,no_update,no_update
    elif trigger==prefix+'-photo-remove' and not viewer_remove:
        return no_update,no_update,no_update
    photos=captioned_refs(photos or [],caption_ids or [],captions or [],prefix)
    message=''
    if trigger==prefix+'-photo-uploaded':
        if not isinstance(uploaded,dict):return no_update,no_update,no_update
        if uploaded.get('error'):return no_update,no_update,str(uploaded['error'])
        if prefix=='dig' and uploaded.get('owner')!=owner:
            raise ValueError('The record changed while the photo was loading. Add it again to this record.')
        photo=uploaded.get('photo')
        validate_refs([photo])
        PhotoStore().check([photo])
        if photo['sha256'] not in {row['sha256'] for row in photos}:photos.append(photo)
        current=photo['sha256']
        validate_refs(photos)
        message='Photo stored locally. Save the observation or record to attach it.'
    elif isinstance(trigger,dict):
        if trigger.get('index') not in {row['sha256'] for row in photos}:return no_update,no_update,no_update
        if trigger.get('type')==prefix+'-photo-remove':
            photos=[row for row in photos if row['sha256']!=trigger['index']]
            message='Removed from this working record. Earlier saved observations retain their photos.'
        elif trigger.get('type')==prefix+'-photo-open':current=trigger['index']
        else:return no_update,no_update,no_update
    elif trigger=='find-photo-remove':
        photos=[row for row in photos if row['sha256']!=current]
        message='Removed from this working observation. Earlier saved notes retain their photos.'
    if current not in {row['sha256'] for row in photos}:current=photos[0]['sha256'] if photos else None
    return photos,current,message


@callback(Output('find-photo-files','data'),Output('find-photo-current','data'),Output('find-photo-status','children'),
    Input('find-photo-uploaded','data'),Input({'type':'find-photo-remove','index':ALL},'n_clicks'),
    Input({'type':'find-photo-open','index':ALL},'n_clicks'),Input('find-photo-remove','n_clicks'),
    State('find-photo-files','data'),State('find-photo-current','data'),
    State({'type':'find-photo-caption','index':ALL},'id'),State({'type':'find-photo-caption','index':ALL},'value'),
    prevent_initial_call=True)
def find_photos(uploaded,remove_clicks,open_clicks,viewer_remove,photos,current,caption_ids,captions):
    try:return update_photos('find',uploaded,remove_clicks,open_clicks,viewer_remove,photos,current,caption_ids,captions)
    except (ValueError,OSError,sqlite3.Error) as error:return no_update,no_update,str(error)


@when_opened('inspect', Output('find-photo-gallery','children'),Output('find-photo-preview','src'),
    Output('find-photo-preview','style'),Output('find-photo-help','style'),
    Input('find-photo-files','data'),Input('find-photo-current','data'))
def render_find_photos(photos,current):
    try:
        photos=validate_refs(photos or [])
        selected=next((row for row in photos if row['sha256']==current),None)
        return gallery(photos,editor='find'),'/clovis/photos/'+current if selected else '',{} if selected else {'display':'none'},{} if not photos else {'display':'none'}
    except (ValueError,OSError,sqlite3.Error) as error:
        return html.P(str(error)), '', {'display':'none'},{}


@when_opened('notebook', Output('dig-photo-files','data'),Output('dig-photo-owner','data'),Input('dig-selection','data'),
    Input('dig-project','value'),Input('dig-new','n_clicks'))
def load_dig_photos(selected,project,new_clicks):
    owner={'project_id':project,'id':selected.get('id') if isinstance(selected,dict) and selected.get('project_id')==project else None}
    try:
        row=DigBook().get(project,owner['id']) if owner['id'] else None
        return row['data'].get('photos',[]) if row else [],owner
    except (ValueError,OSError,sqlite3.Error):return [],owner


@callback(Output('dig-photo-files','data',allow_duplicate=True),Output('dig-photo-status','children'),
    Input('dig-photo-uploaded','data'),Input({'type':'dig-photo-remove','index':ALL},'n_clicks'),
    State('dig-photo-files','data'),State('dig-photo-owner','data'),
    State({'type':'dig-photo-caption','index':ALL},'id'),State({'type':'dig-photo-caption','index':ALL},'value'),
    prevent_initial_call=True)
def edit_dig_photos(uploaded,remove_clicks,photos,owner,caption_ids,captions):
    try:
        refs,_,message=update_photos('dig',uploaded,remove_clicks,[],0,photos,None,caption_ids,captions,owner)
        return refs,message
    except (ValueError,OSError,sqlite3.Error) as error:return no_update,str(error)


@when_opened('notebook', Output('dig-photo-gallery','children'),Input('dig-photo-files','data'))
def render_dig_photos(photos):
    try:return gallery(photos or [],editor='dig')
    except (ValueError,OSError,sqlite3.Error) as error:return html.P(str(error))


@when_opened('notebook', Output('fieldbook-photos','children'),Input('fieldbook-store','data'),Input('fieldbook-selected','value'))
def read_fieldbook_photos(book,selected):
    from atlas.gui.fieldbook_callbacks import selected_rows
    try:
        row,_=selected_rows(book,selected)
        return gallery(row.get('photos',[])) if row else []
    except (ValueError,OSError,sqlite3.Error) as error:return html.P(str(error))
