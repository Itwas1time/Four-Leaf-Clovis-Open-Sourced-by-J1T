/* A provider image can fail while the offline source record remains useful. */
(() => {
  document.addEventListener('error', event => {
    const picture = event.target;
    if (!(picture instanceof HTMLImageElement) || !picture.classList.contains('clovis-library-image')) return;
    const frame = picture.closest('[data-library-image]');
    if (!frame || frame.querySelector('[data-reference-image-error]')) return;
    picture.hidden = true;
    const message = document.createElement('p');
    message.setAttribute('data-reference-image-error', '');
    message.setAttribute('role', 'status');
    message.className = 'atlas-help';
    message.textContent = 'The reference photograph could not load. The source record remains readable.';
    frame.appendChild(message);
  }, true);
})();
