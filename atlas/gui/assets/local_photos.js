/* Original files go only to this local Clovis server; Dash stores references. */
(() => {
  'use strict';
  function openGalleryImage(image) {
    const source=image.getAttribute('data-clovis-photo-src') || '';
    if (!/^\/clovis\/photos\/[a-f0-9]{64}$/.test(source)) return;
    image.loading='lazy'; image.src=source;
    image.removeAttribute('data-clovis-photo-src');
  }
  function scanImages(root) {
    if (root.matches?.('img[data-clovis-photo-src]')) openGalleryImage(root);
    root.querySelectorAll?.('img[data-clovis-photo-src]').forEach(openGalleryImage);
  }
  new MutationObserver(records => records.forEach(record => {
    if (record.type==='attributes') openGalleryImage(record.target);
    else record.addedNodes.forEach(scanImages);
  })).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['data-clovis-photo-src']});
  scanImages(document);
  const noUpdate = () => window.dash_clientside.no_update;
  function chooser(accept,handle) {
    return new Promise(resolve => {
      const input = document.createElement('input');
      input.type = 'file'; input.accept = accept; input.hidden = true;
      document.body.append(input);
      input.addEventListener('cancel', () => {input.remove(); resolve(null);}, {once:true});
      input.addEventListener('change', async () => {
        const file = input.files[0]; input.remove();
        if (!file) {resolve(null); return;}
        try {resolve(await handle(file));}
        catch (error) {resolve({error:error.message || 'The local file could not be opened.'});}
      }, {once:true});
      input.click();
    });
  }
  async function responseJSON(response) {
    let result;
    try {result = await response.json();}
    catch (_) {throw new Error('The local app could not process this file.');}
    if (!response.ok) throw new Error(result.error || 'The local file could not be saved.');
    return result;
  }
  async function choosePhoto(clicks,prefix,owner) {
    if (!clicks) return noUpdate();
    const result = await chooser('image/jpeg,image/png,image/webp', async file => {
      if (file.size > 5000000) throw new Error('Choose a photo under 5 MB.');
      window.dash_clientside.set_props(prefix+'-photo-transfer',{data:{busy:true}});
      try {
        const response = await fetch('/clovis/photos',{method:'POST',credentials:'same-origin',
          headers:{'Content-Type':'application/octet-stream','X-Clovis-Photo':'1','X-Clovis-Photo-Name':encodeURIComponent(file.name)},body:file});
        return {photo:await responseJSON(response),owner,nonce:crypto.randomUUID()};
      } finally {
        window.dash_clientside.set_props(prefix+'-photo-transfer',{data:{busy:false}});
      }
    });
    return result ? {...result,nonce:crypto.randomUUID()} : noUpdate();
  }
  async function downloadBook(clicks,book) {
    if (!clicks) return noUpdate();
    window.dash_clientside.set_props('fieldbook-transfer-status',{children:'Preparing your fieldbook backup…'});
    try {
      const response = await fetch('/clovis/fieldbook/backup',{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-Clovis-Fieldbook-Backup':'1'},body:JSON.stringify(book)});
      if (!response.ok) await responseJSON(response);
      const isZIP = (response.headers.get('Content-Type') || '').includes('application/zip');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href=url; link.download=isZIP?'clovis-fieldbook.zip':'clovis-fieldbook.json';
      document.body.append(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url),10000);
      return isZIP?'Downloaded the fieldbook with its original photos.':'Downloaded the fieldbook JSON backup.';
    } catch (error) {return error.message || 'The fieldbook could not be downloaded.';}
  }
  async function restoreBook(clicks,book) {
    if (!clicks) return [noUpdate(),noUpdate()];
    const result = await chooser('.json,.zip,application/json,application/zip', async file => {
      window.dash_clientside.set_props('fieldbook-transfer-status',{children:'Checking and restoring the fieldbook and original photos…'});
      const body = new FormData();
      body.append('backup',file); body.append('current',JSON.stringify(book));
      return responseJSON(await fetch('/clovis/fieldbook/restore',{method:'POST',credentials:'same-origin',
        headers:{'X-Clovis-Fieldbook-Backup':'1'},body}));
    });
    if (!result) return [noUpdate(),'Restore cancelled.'];
    if (result.error) return [noUpdate(),result.error];
    return [{book:result.book,nonce:crypto.randomUUID()},'Restored the fieldbook and its original photos on this computer.'];
  }
  let readingSyncGeneration=0;
  async function autosyncWorkspaceReadings(book) {
    const generation=++readingSyncGeneration;
    if (!book || !Array.isArray(book.entries)) return noUpdate();
    window.dash_clientside.set_props('workspace-autosync-status',{children:'Checking saved readings...'});
    try {
      const result=await responseJSON(await fetch('/clovis/workspace/sync-readings',{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-Clovis-Workspace':'1'},body:JSON.stringify(book)}));
      if (generation!==readingSyncGeneration) return noUpdate();
      const known=new Map(book.entries.map(row => [row.id,row]));
      if (result.book.entries.some(row => !known.has(row.id) || known.get(row.id).markdown !== row.markdown)) {
        window.dash_clientside.set_props('fieldbook-reconciled',{data:{book:result.book,nonce:crypto.randomUUID()}});
        return 'Reopening readings saved in the local workspace...';
      }
      return result.book.entries.length?'Readings also saved in the local workspace.':'No readings saved yet.';
    } catch(error) {
      return generation===readingSyncGeneration?'Local workspace copy failed: '+(error.message || 'try Sync saved readings.')+' The browser copy remains.':noUpdate();
    }
  }
  async function syncWorkspaceReadings(clicks,book) {
    if (!clicks) return [noUpdate(),noUpdate()];
    window.dash_clientside.set_props('workspace-transfer-status',{children:'Merging saved readings...'});
    try {
      const result=await responseJSON(await fetch('/clovis/workspace/sync-readings',{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-Clovis-Workspace':'1'},body:JSON.stringify(book)}));
      return [{book:result.book,nonce:crypto.randomUUID()},'Readings saved in the local app. Check the fieldbook status for the browser merge.'];
    } catch(error) {return [noUpdate(),error.message || 'Readings could not be synced.'];}
  }
  async function downloadWorkspace(clicks,book) {
    if (!clicks) return noUpdate();
    window.dash_clientside.set_props('workspace-transfer-status',{children:'Preparing complete workspace backup...'});
    try {
      const response=await fetch('/clovis/workspace/backup',{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-Clovis-Workspace':'1'},body:JSON.stringify(book)});
      if (!response.ok) await responseJSON(response);
      const url=URL.createObjectURL(await response.blob()), link=document.createElement('a');
      link.href=url; link.download='clovis-workspace.zip'; document.body.append(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url),10000);
      return 'Downloaded the complete workspace backup. Keep a copy on another device.';
    } catch(error) {return error.message || 'The workspace could not be backed up.';}
  }
  async function restoreWorkspace(clicks,book) {
    if (!clicks) return [noUpdate(),noUpdate()];
    const result=await chooser('.zip,application/zip',async file => {
      window.dash_clientside.set_props('workspace-transfer-status',{children:'Checking the complete workspace backup...'});
      const body=new FormData(); body.append('backup',file); body.append('current',JSON.stringify(book));
      return responseJSON(await fetch('/clovis/workspace/restore',{method:'POST',credentials:'same-origin',
        headers:{'X-Clovis-Workspace':'1'},body}));
    });
    if (!result) return [noUpdate(),'Restore cancelled.'];
    if (result.error) return [noUpdate(),result.error];
    window.dash_clientside.set_props('dig-refresh',{data:Date.now()});
    return [{book:result.book,nonce:crypto.randomUUID()},'Workspace restored. Choose a project in Dig records; readings are also retained by the local app.'];
  }
  async function downloadQuestionPhotos(clicks,book,selected,question,comparison,detail,draft) {
    if (!clicks || !book?.entries?.find(row => row.id===selected)?.photos?.length) return noUpdate();
    try {
      const response=await fetch('/clovis/fieldbook/question-backup',{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-Clovis-Fieldbook-Backup':'1'},
        body:JSON.stringify({book,selected,question,comparison,detail,draft})});
      if (!response.ok) await responseJSON(response);
      const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');
      link.href=url; link.download='clovis-question-packet.zip';
      document.body.append(link);link.click();link.remove();
      setTimeout(() => URL.revokeObjectURL(url),10000);
      return 'Downloaded the question packet with its original photos. No message was sent.';
    } catch(error) {return error.message || 'The question packet could not be downloaded.';}
  }
  window.dash_clientside = Object.assign({},window.dash_clientside,{
    clovisLocalPhotos:{
      chooseFindPhoto:clicks => choosePhoto(clicks,'find',null),
      chooseDigPhoto:(clicks,project,selected) => choosePhoto(clicks,'dig',{project_id:project,id:selected?.id || null}),
      downloadBook,restoreBook,autosyncWorkspaceReadings,syncWorkspaceReadings,downloadWorkspace,restoreWorkspace,downloadQuestionPhotos
    }
  });
})();
