/* A local File body avoids base64 amplification in ordinary Dash requests. */
(() => {
  let active = false;
  const props = (id, values) => window.dash_clientside.set_props(id, values);
  const message = text => props('dig-status', {children: text});

  async function restore(file, button) {
    if (active) return message('A project backup is already being restored.');
    if (!file.name.toLowerCase().endsWith('.zip')) return message('Choose a Clovis project ZIP backup.');
    if (file.size > Number(button.dataset.maxBytes)) return message('The backup exceeds its project notes and 100 MB photo allowance.');
    active = true;
    button.disabled = true;
    message('Restoring the project backup on this computer…');
    try {
      const response = await fetch('/clovis/dig-records/restore-backup', {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/zip', 'X-Clovis-Project-Backup': '1'}, body: file,
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data?.project_id) throw new Error(data?.error || 'The project backup transfer was interrupted. Choose the ZIP again.');
      props('dig-upload-restored', {data: {...data, nonce: Date.now()}});
    } catch (error) {
      message(error.message || 'The project backup could not be restored. Existing records were preserved.');
    } finally {
      active = false;
      button.disabled = false;
      button.focus({preventScroll: true});
    }
  }

  document.addEventListener('click', event => {
    const button = event.target.closest?.('#dig-restore-backup');
    if (!button || button.disabled) return;
    if (active) return message('A project backup is already being restored.');
    const input = document.createElement('input');
    input.type = 'file'; input.accept = '.zip,application/zip'; input.hidden = true;
    input.addEventListener('change', () => {
      const file = input.files?.[0]; input.remove();
      if (file) restore(file, button);
    }, {once: true});
    input.addEventListener('cancel', () => input.remove(), {once: true});
    document.body.append(input); input.click();
  });
})();
