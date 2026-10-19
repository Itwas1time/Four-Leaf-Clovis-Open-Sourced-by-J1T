/* File slices go only to this local app. No whole-file/base64 callback payload. */
(() => {
  let active = null;
  const props = (id, values) => window.dash_clientside.set_props(id, values);
  const collectionTitle = button => button.closest('.clovis-pack-card')?.querySelector('h3')?.textContent || 'Selected collection';
  const message = (text, title = active?.title || '') => props('data-pack-start-status', {children: title ? title + ' · ' + text : text});
  const cancelEnabled = enabled => props('data-pack-cancel-local', {disabled: !enabled, style: {display: enabled ? '' : 'none'}});
  const endpoint = key => '/clovis/collections/local' + (key ? '/' + encodeURIComponent(key) : '');
  const headers = {'X-Clovis-Local-Upload': '1'};

  async function request(url, options) {
    const response = await fetch(url, {...options, credentials: 'same-origin'});
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(data?.error || 'The local ZIP transfer was interrupted. Choose the ZIP again.');
    return data;
  }

  async function transfer(file, button) {
    if (active) return message('A ZIP transfer is already running. See Collection installation status.');
    if (file.size !== Number(button.dataset.clovisBytes)) {
      return message('This ZIP size does not match this collection snapshot. Choose its official ZIP.', collectionTitle(button));
    }
    const state = {key: null, controller: new AbortController(), transferring: true, title: collectionTitle(button)};
    active = state;
    message('Preparing the local ZIP transfer…');
    try {
      const started = await request(endpoint(), {method: 'POST', headers: {...headers, 'Content-Type': 'application/json'},
        body: JSON.stringify({collection: button.dataset.clovisPack, bytes: file.size})});
      state.key = started.id;
      cancelEnabled(true);
      props('data-pack-job', {data: state.key});
      props('data-pack-poll', {disabled: false});
      message('Transferring the ZIP to Clovis on this computer.');
      let offset = 0;
      while (offset < file.size) {
        const end = Math.min(file.size, offset + started.chunk_bytes);
        const result = await request(endpoint(state.key), {method: 'PUT',
          headers: {...headers, 'Content-Type': 'application/octet-stream', 'X-Clovis-Offset': String(offset)},
          body: file.slice(offset, end), signal: state.controller.signal});
        if (result.received !== end) throw new Error('The local ZIP transfer offset did not match. Choose the ZIP again.');
        offset = end;
      }
      state.transferring = false;
      cancelEnabled(false);
      await request(endpoint(state.key) + '/finish', {method: 'POST', headers});
      message('ZIP transfer complete. Installation status appears below.');
    } catch (error) {
      if (state.key) {
        await request(endpoint(state.key), {method: 'DELETE', headers}).catch(() => {});
      }
      message(state.controller.signal.aborted ? 'ZIP transfer cancelled. Choose a ZIP to start again.' :
        (error.message || 'ZIP transfer interrupted. Choose the ZIP again.'));
    } finally {
      active = null;
      cancelEnabled(false);
      button.focus({preventScroll: true});
    }
  }

  document.addEventListener('click', event => {
    if (event.target.closest?.('#data-pack-cancel-local')) {
      if (active?.transferring) active.controller.abort();
      return;
    }
    const button = event.target.closest?.('button[data-clovis-pack]');
    if (!button || button.disabled) return;
    if (active) return message('A ZIP transfer is already running. See Collection installation status.');
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.zip,application/zip';
    input.hidden = true;
    input.addEventListener('change', () => {
      const file = input.files?.[0];
      input.remove();
      if (file) transfer(file, button);
    }, {once: true});
    input.addEventListener('cancel', () => input.remove(), {once: true});
    document.body.append(input);
    input.click();
  });

  window.addEventListener('beforeunload', () => {
    if (active?.key && active.transferring) {
      fetch(endpoint(active.key), {method: 'DELETE', headers, credentials: 'same-origin', keepalive: true}).catch(() => {});
    }
  });
})();
