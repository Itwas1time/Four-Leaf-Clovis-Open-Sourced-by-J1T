// Focus the existing note field; opening a prompt never changes observations.
document.addEventListener('click', function(event) {
    const link = event.target.closest && event.target.closest('.clovis-record-detail');
    if (!link) return;
    const notes = document.getElementById('find-notes');
    if (!notes) return;
    event.preventDefault();
    notes.scrollIntoView({block:'center',behavior:'auto'});
    notes.focus({preventScroll:true});
});
