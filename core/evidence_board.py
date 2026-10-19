"""Structured evidence derived exclusively from a current server-owned report."""
from core.fossil_guides import matching_guides

STATUS = {
    'not_requested': 'Online rock maps were not requested.',
    'no_coverage': 'No online map unit was returned at the public town point. This does not establish an absence of rocks or fossils.',
    'unavailable': 'Online rock maps are unavailable. This is a data gap, not evidence of no finds.',
    'available': 'Online mapped geology at the public Census town point; local soil and imported fill may differ.',
}
USGS_SOURCE = 'https://ngmdb.usgs.gov/Prodesc/proddesc_118545.htm'
USGS_SCOPE = ('USGS Cooperative National Geologic Map v2 (2026), 1:500,000 scale. '
              'Separate map themes intersect the public Census town point; they are not a measured soil profile or a property assessment.')


def offline_units(report):
    if not isinstance(report, dict):
        return []
    knowledge = report.get('knowledge')
    return knowledge.get('usgs_units', []) if isinstance(knowledge, dict) else []


def note_contexts(report):
    """Canonical source choices from the current server-owned town report."""
    if not isinstance(report, dict):
        return {}
    result = {}
    if report.get('geology_status') == 'available':
        for unit in report.get('units', []):
            result[f"unit-{unit['map_id']}"] = {
                'title': unit['name'][:200], 'date': unit.get('interval', '')[:120],
                'source': unit['reference'][:1600]}
    for unit in offline_units(report):
        source = (f"{USGS_SOURCE} · USGS CNGM v2 (2026) · {unit['layer_label']} · "
                  f"unit {unit['id']} / {unit['map_unit']} · 1:500,000 · "
                  f"Census town point {report.get('place', {}).get('geoid', '')}; not a property assessment")
        result['usgs-' + unit['id']] = {
            'title': unit['name'][:200], 'date': (unit.get('age') or '')[:120], 'source': source[:1600]}
    return result


def note_context(report, selected_id):
    """Bounded literal map context from a server report, never browser fields."""
    if not isinstance(selected_id, str):
        return None
    return note_contexts(report).get(selected_id)


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
    offline = offline_units(report)
    for unit in offline:
        cards.append({'id': 'usgs-' + unit['id'], 'kind': 'Offline USGS map unit',
                      'title': unit['name'], 'materials': unit.get('geomaterial') or 'Materials not supplied',
                      'age': unit.get('age') or 'Age not supplied',
                      'description': unit.get('description') or 'Description not supplied',
                      'reference': USGS_SCOPE, 'reference_url': USGS_SOURCE,
                      'usgs_id': unit['id'], 'map_unit': unit['map_unit'], 'map_theme': unit['layer_label'],
                      'source_units': unit.get('source_units', []), 'source_citations': unit.get('source_citations', [])})
    # Recompute from the reviewed catalogue. Provider fossil words never create a specimen claim.
    state = report.get('place', {}).get('state', '')
    for index, guide in enumerate(matching_guides(state, units)):
        cards.append({'id': f'guide-{index}', 'kind': 'Reviewed formation guide', 'title': guide['name'],
                      'materials': guide['examples'], 'age': 'Formation context; no local specimen documented',
                      'description': 'These are documented examples associated with this formation in the cited guide. A name match does not establish occurrence at this town or property.',
                      'reference': guide['source_name'], 'url': guide['source'],
                      'scope_url': guide.get('scope_source')})
    message = STATUS.get(status, 'Online rock-map status is unknown.')
    if offline:
        message += f' {len(offline)} offline USGS map themes are available below. Separate themes are not layers in a measured soil profile.'
    return {'status': message, 'cards': cards,
            'checked_at': report.get('geology_checked_at', '')}
