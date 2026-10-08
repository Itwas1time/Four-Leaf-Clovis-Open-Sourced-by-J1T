"""Structured evidence derived exclusively from a current server-owned report."""
from core.fossil_guides import matching_guides

STATUS = {
    'not_requested': 'Offline report: regional geology was not requested.',
    'no_coverage': 'No map unit was returned at the public town point. This does not establish an absence of rocks or fossils.',
    'unavailable': 'Regional geology is unavailable. This is a data gap, not evidence of no finds.',
    'available': 'Mapped geology at the public Census town point; local soil and imported fill may differ.',
}


def note_context(report, selected_id):
    """Bounded literal map context from a server report, never browser fields."""
    if not isinstance(report, dict) or report.get('geology_status') != 'available':
        return None
    if not isinstance(selected_id, str):
        return None
    for unit in report.get('units', []):
        if selected_id == f"unit-{unit['map_id']}":
            return {'title': unit['name'][:200], 'date': unit.get('interval', '')[:120],
                    'source': unit['reference'][:1600]}
    return None


def evidence_board(report):
    """Preserve separate map sources; never turn geology into find odds."""
    if not isinstance(report, dict):
        return {'status': 'Choose a town and select Explore this town to build current evidence.', 'cards': []}
    status = report.get('geology_status')
    units = report.get('units', []) if status == 'available' else []
    cards = []
    for unit in units:
        cards.append({'id': f"unit-{unit['map_id']}", 'kind': 'Mapped rock unit',
                      'title': unit['name'], 'materials': unit.get('lithology') or 'Materials not supplied',
                      'age': unit.get('interval') or 'Age not supplied',
                      'description': unit.get('description') or 'Description not supplied',
                      'comments': unit.get('comments', ''), 'reference': unit['reference'],
                      'source_id': unit['source_id'], 'map_id': unit['map_id']})
    # Recompute from the reviewed catalogue. Provider fossil words never create a specimen claim.
    state = report.get('place', {}).get('state', '')
    for index, guide in enumerate(matching_guides(state, units)):
        cards.append({'id': f'guide-{index}', 'kind': 'Reviewed formation guide', 'title': guide['name'],
                      'materials': guide['examples'], 'age': 'Formation context; no local specimen documented',
                      'description': 'These are documented examples associated with this formation in the cited guide. A name match does not establish occurrence at this town or property.',
                      'reference': guide['source_name'], 'url': guide['source'],
                      'scope_url': guide.get('scope_source')})
    return {'status': STATUS.get(status, 'Regional geology status is unknown.'), 'cards': cards,
            'checked_at': report.get('geology_checked_at', '')}
