(function () {
  'use strict';
  const MIN_ZOOM = 0.25, MAX_ZOOM = 12, PAD = 12;
  const finite = (value, fallback = 0) => Number.isFinite(value) ? value : fallback;
  const clamp = (value, low, high) => Math.min(high, Math.max(low, finite(value, low)));
  const normalizedAngle = angle => ((finite(angle) % 360) + 360) % 360;
  function dimensions(state) {
    return normalizedAngle(state.angle) % 180 === 0
      ? [state.width, state.height] : [state.height, state.width];
  }
  function fitScale(state, boxWidth, boxHeight) {
    const [width, height] = dimensions(state);
    return Math.max(Number.EPSILON, Math.min(1,
      Math.max(1, boxWidth - 2 * PAD) / Math.max(1, width),
      Math.max(1, boxHeight - 2 * PAD) / Math.max(1, height)));
  }
  function bounded(state, boxWidth, boxHeight) {
    state.zoom = clamp(state.zoom, MIN_ZOOM, MAX_ZOOM);
    state.angle = normalizedAngle(state.angle);
    const [width, height] = dimensions(state), scale = state.base * state.zoom;
    // Small images may move within their free margin, staying fully visible.
    // This also preserves a center detail when rotation swaps the long axis.
    const axisLimit = (displaySize, viewportSize) => displaySize <= viewportSize
      ? (viewportSize - displaySize) / 2 : (displaySize - viewportSize) / 2 + PAD;
    const maxX = axisLimit(width * scale, boxWidth);
    const maxY = axisLimit(height * scale, boxHeight);
    state.x = clamp(state.x, -maxX, maxX);
    state.y = clamp(state.y, -maxY, maxY);
    return state;
  }
  function zoomAt(state, zoom, x = 0, y = 0) {
    const next = clamp(zoom, MIN_ZOOM, MAX_ZOOM), ratio = next / state.zoom;
    state.x = finite(x) - (finite(x) - state.x) * ratio;
    state.y = finite(y) - (finite(y) - state.y) * ratio;
    state.zoom = next;
    return state;
  }
  function rotate(state, boxWidth, boxHeight) {
    const oldScale = state.base * state.zoom;
    state.angle = normalizedAngle(state.angle + 90);
    state.base = fitScale(state, boxWidth, boxHeight);
    const ratio = state.base * state.zoom / oldScale, oldX = state.x;
    state.x = -state.y * ratio;
    state.y = oldX * ratio;
    return bounded(state, boxWidth, boxHeight);
  }
  // Pure geometry is available to private Node tests, without a browser global.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {fitScale, bounded, zoomAt, rotate};
  }
  if (typeof document === 'undefined') return;

  const mounted = new WeakMap();
  function attach(root) {
    if (mounted.has(root)) return;
    const image = root.querySelector('#find-photo-preview');
    const viewport = root.querySelector('#find-photo-viewport');
    const status = root.querySelector('#find-photo-view-status');
    const toolbar = root.querySelector('.clovis-photo-toolbar');
    const help = root.querySelector('#find-photo-view-help');
    const remove = root.querySelector('#find-photo-remove');
    if (!image || !viewport || !status || !toolbar || !help || !remove) return;
    let state = {width: 1, height: 1, zoom: 1, base: 1, angle: 0, x: 0, y: 0};
    let source = '', ready = false, lastDisplay = image.style.display;
    const pointers = new Map();
    const box = () => [viewport.clientWidth, viewport.clientHeight];
    const buttons = Array.from(toolbar.querySelectorAll('button'));
    function announce() {
      const text = Math.round(state.zoom * 100) + '% of fit · ' + state.angle + '°';
      if (status.textContent !== text) status.textContent = text;
      root.querySelector('#find-photo-zoom-in').disabled = state.zoom >= MAX_ZOOM;
      root.querySelector('#find-photo-zoom-out').disabled = state.zoom <= MIN_ZOOM;
    }
    function paint() {
      if (!ready) return;
      const [width, height] = box();
      if (width <= 0 || height <= 0) return;
      bounded(state, width, height);
      image.style.width = state.width + 'px';
      image.style.height = state.height + 'px';
      image.style.transform = 'translate(-50%, -50%) translate(' + state.x + 'px, ' + state.y +
        'px) rotate(' + state.angle + 'deg) scale(' + (state.base * state.zoom) + ')';
      announce();
    }
    function reset() {
      pointers.clear();
      viewport.classList.remove('is-panning');
      state = {width: 1, height: 1, zoom: 1, base: 1, angle: 0, x: 0, y: 0};
      ready = false;
      root.hidden = true;
      root.dataset.photoState = 'empty';
      viewport.hidden = false;
      toolbar.hidden = false;
      help.hidden = false;
      remove.disabled = true;
      status.textContent = '';
      buttons.forEach(button => {button.disabled = true;});
      image.style.transform = '';
    }
    function loaded() {
      if (!source || image.getAttribute('src') !== source || image.style.display === 'none' ||
          !image.complete || image.naturalWidth <= 0 || image.naturalHeight <= 0) return;
      state.width = image.naturalWidth;
      state.height = image.naturalHeight;
      ready = true;
      root.hidden = false;
      root.dataset.photoState = 'ready';
      remove.disabled = false;
      buttons.forEach(button => {button.disabled = false;});
      const [width, height] = box();
      state.base = fitScale(state, width, height);
      paint();
    }
    function sync() {
      const next = image.getAttribute('src') || '';
      if (!next || image.style.display === 'none') {
        source = '';
        if (ready || !root.hidden) reset();
        return;
      }
      if (next === source) return;
      reset();
      // Only local formats approved by the upload callback; never load a URL here.
      if (next.length > 6700000 || !/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(next)) {
        source = '';
        root.dataset.photoState = 'rejected';
        return;
      }
      source = next;
      root.dataset.photoState = 'loading';
      if (image.complete) loaded();
    }
    image.addEventListener('load', loaded);
    image.addEventListener('error', () => {
      if (!source || image.getAttribute('src') !== source) return;
      reset();
      source = '';
      root.dataset.photoState = 'error';
      viewport.hidden = true;
      toolbar.hidden = true;
      help.hidden = true;
      root.hidden = false;
      remove.disabled = false;
      status.textContent = 'This photo could not be opened. Try another JPEG, PNG or WebP photo.';
    });
    const imageObserver = new MutationObserver(records => {
      const changedSource = records.some(record => record.attributeName === 'src');
      const display = image.style.display;
      if (changedSource || display !== lastDisplay) {
        lastDisplay = display;
        sync();
      }
    });
    imageObserver.observe(image, {attributes: true, attributeFilter: ['src', 'style']});
    function fit() {
      if (!ready) return;
      state.zoom = 1;
      state.x = state.y = 0;
      state.base = fitScale(state, ...box());
      paint();
    }
    function changeZoom(factor, x = 0, y = 0) {
      if (!ready) return;
      zoomAt(state, state.zoom * factor, x, y);
      paint();
    }
    const turn = () => {if (ready) {rotate(state, ...box()); paint();}};
    root.querySelector('#find-photo-zoom-in').addEventListener('click', () => changeZoom(1.4));
    root.querySelector('#find-photo-zoom-out').addEventListener('click', () => changeZoom(1 / 1.4));
    root.querySelector('#find-photo-rotate').addEventListener('click', turn);
    root.querySelector('#find-photo-fit').addEventListener('click', fit);
    remove.addEventListener('click', () => {
      if (!window.dash_clientside || typeof window.dash_clientside.set_props !== 'function') return;
      source = '';
      reset();
      // The existing upload callback clears src, help, and notice locally.
      // No image data enters a store, server callback, or persistent storage.
      window.dash_clientside.set_props('find-photo', {contents: null, filename: null});
    });
    viewport.addEventListener('wheel', event => {
      if (!ready) return;
      event.preventDefault();
      const rect = viewport.getBoundingClientRect();
      const delta = clamp(event.deltaY, -120, 120);
      changeZoom(Math.exp(-delta * 0.003), event.clientX - rect.left - rect.width / 2,
        event.clientY - rect.top - rect.height / 2);
    }, {passive: false});
    viewport.addEventListener('keydown', event => {
      if (!ready || event.altKey || event.ctrlKey || event.metaKey) return;
      const key = event.key.toLowerCase();
      if (key === '+' || key === '=') changeZoom(1.4);
      else if (key === '-' || key === '_') changeZoom(1 / 1.4);
      else if (key === 'r') turn();
      else if (key === 'f' || key === '0') fit();
      else if (key === 'arrowleft') {state.x += 32; paint();}
      else if (key === 'arrowright') {state.x -= 32; paint();}
      else if (key === 'arrowup') {state.y += 32; paint();}
      else if (key === 'arrowdown') {state.y -= 32; paint();}
      else return;
      event.preventDefault();
      event.stopPropagation();
    });
    viewport.addEventListener('pointerdown', event => {
      if (!ready || event.button !== 0) return;
      if (pointers.size >= 2) return;
      pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
      viewport.setPointerCapture(event.pointerId);
      viewport.classList.add('is-panning');
      viewport.focus({preventScroll: true});
      event.preventDefault();
    });
    viewport.addEventListener('pointermove', event => {
      if (!ready || !pointers.has(event.pointerId)) return;
      const old = Array.from(pointers.values());
      const previous = pointers.get(event.pointerId);
      pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
      if (pointers.size === 1) {
        state.x += event.clientX - previous.x;
        state.y += event.clientY - previous.y;
      } else {
        const next = Array.from(pointers.values());
        const midpoint = pair => ({x: (pair[0].x + pair[1].x) / 2, y: (pair[0].y + pair[1].y) / 2});
        const distance = pair => Math.hypot(pair[0].x - pair[1].x, pair[0].y - pair[1].y);
        const before = midpoint(old), after = midpoint(next), rect = viewport.getBoundingClientRect();
        const ratio = clamp(distance(next) / Math.max(1, distance(old)), 0.5, 2);
        zoomAt(state, state.zoom * ratio, before.x - rect.left - rect.width / 2,
          before.y - rect.top - rect.height / 2);
        state.x += after.x - before.x;
        state.y += after.y - before.y;
      }
      paint();
      event.preventDefault();
    });
    const endPointer = event => {
      pointers.delete(event.pointerId);
      if (!pointers.size) viewport.classList.remove('is-panning');
    };
    viewport.addEventListener('pointerup', endPointer);
    viewport.addEventListener('pointercancel', endPointer);
    viewport.addEventListener('lostpointercapture', endPointer);
    const resize = new ResizeObserver(() => {
      if (!ready) return;
      const [width, height] = box();
      if (width <= 0 || height <= 0) return;
      const oldBase = state.base;
      state.base = fitScale(state, width, height);
      // Preserve the center detail and relative zoom as the workbench resizes.
      state.x *= state.base / oldBase;
      state.y *= state.base / oldBase;
      paint();
    });
    resize.observe(viewport);
    mounted.set(root, {imageObserver, resize});
    reset();
    sync();
  }
  function discover() {
    const root = document.getElementById('find-photo-viewer');
    if (root) attach(root);
  }
  const observer = new MutationObserver(discover);
  function start() {
    discover();
    observer.observe(document.body, {childList: true, subtree: true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
