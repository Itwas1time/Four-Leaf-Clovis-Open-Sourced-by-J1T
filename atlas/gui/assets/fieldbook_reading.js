(() => {
  let returnFocus = null;
  document.addEventListener('click', event => {
    const opener = event.target.closest?.('#fieldbook-read-full, #dig-read-full');
    if (!opener || opener.disabled) return;
    const projectSource = opener.id === 'dig-read-full';
    const title = document.getElementById(projectSource ? 'dig-record-title' : 'fieldbook-title');
    const notes = document.getElementById(projectSource ? 'dig-cited-note-text' : 'fieldbook-text');
    if (!title || !notes || !notes.textContent.trim()) return;
    let dialog = document.getElementById('fieldbook-full-reader');
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'fieldbook-full-reader';
      dialog.className = 'clovis-note-dialog';
      dialog.setAttribute('aria-labelledby', 'fieldbook-full-title');
      const header = document.createElement('div');
      header.className = 'clovis-note-dialog-header';
      const heading = document.createElement('h2');
      heading.id = 'fieldbook-full-title';
      const close = document.createElement('button');
      close.type = 'button';
      close.className = 'atlas-secondary-button';
      close.textContent = 'Close full notes';
      close.addEventListener('click', () => dialog.close());
      header.append(heading, close);
      const content = document.createElement('pre');
      content.className = 'clovis-note-dialog-text';
      dialog.append(header, content);
      dialog.addEventListener('close', () => returnFocus?.focus({preventScroll:true}));
      document.body.append(dialog);
    }
    // Saved/imported prose is copied as text, never as active markup.
    dialog.querySelector('h2').textContent = title.textContent;
    dialog.querySelector('pre').textContent = notes.textContent;
    returnFocus = opener;
    if (!dialog.open) dialog.showModal();
    dialog.querySelector('button').focus({preventScroll:true});
  });
})();
