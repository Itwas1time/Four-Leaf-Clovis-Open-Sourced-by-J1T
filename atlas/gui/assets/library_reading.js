/* Keep the selected source readable; searches and saved notes remain intact. */
(() => {
  let pending = null;
  let timer = null;
  const stop = () => { if (pending) { pending.disconnect(); pending = null; } if (timer) { clearTimeout(timer); timer = null; } };
  const read = detail => {
    const heading = detail.querySelector('h3');
    if (!heading) return;
    stop();
    detail.scrollIntoView({block:'start',behavior:'smooth'});
    heading.tabIndex = -1;
    heading.focus({preventScroll:true});
  };
  document.addEventListener('click', event => {
    const back = event.target.closest('button[data-library-back]');
    if (back) {
      stop();
      const query = document.getElementById(back.dataset.libraryBack);
      if (query) { query.scrollIntoView({block:'start',behavior:'smooth'}); query.focus({preventScroll:true}); }
      return;
    }
    const button = event.target.closest('button.clovis-library-record');
    if (!button) return;
    const split = button.closest('.clovis-library-split');
    const detail = split && split.querySelector('article.clovis-library-detail');
    if (!detail) return;
    split.querySelectorAll('button.clovis-library-record').forEach(item => item.setAttribute('aria-pressed',item===button?'true':'false'));
    stop();
    const before = detail.querySelector('h3')?.textContent;
    if (before && before === button.querySelector('strong')?.textContent) { read(detail); return; }
    pending = new MutationObserver(() => {
      const heading = detail.querySelector('h3');
      if (heading && heading.textContent !== before) read(detail);
    });
    pending.observe(detail,{childList:true,subtree:true,characterData:true});
    timer=setTimeout(stop,10000);
  });
})();
