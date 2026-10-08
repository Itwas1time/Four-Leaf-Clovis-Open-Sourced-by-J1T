"""Observation-led comparisons, with no inferred dates, values or probabilities."""
from core.resident_context import _md
from core.us_places import get_place

MATERIALS = {
    'unknown': 'I am not sure yet', 'glass': 'Glass or glass-like',
    'ceramic': 'Pottery, ceramic or brick', 'metal': 'Metal',
    'rock': 'Rock or mineral', 'fossil': 'Possible fossil or patterned rock',
    'bone': 'Possible bone or tooth',
}
SETTINGS = {'unknown': 'I do not know', 'surface': 'Already exposed on the surface',
            'fill': 'Loose or imported soil / gravel', 'attached': 'Attached to rock',
            'building': 'Near an old building or building debris'}
FEATURES = {
    'transparent': 'Light passes through it', 'curved': 'Curved wall or rim',
    'seam': 'A straight raised seam', 'mark': 'Letters, numbers or a maker’s mark',
    'glaze': 'A smooth coating over a grainy body', 'grain': 'Visible grains or crystals',
    'layers': 'Layers or bands', 'shell': 'Shell-like ribs or spiral',
    'branch': 'A flat branching pattern', 'holes': 'Regular holes or worked edges',
    'rust': 'Rust or other corrosion', 'porous': 'Pores or a hollow interior',
}
FEATURE_QUESTIONS = {
    'transparent': 'Where does light pass through it: the whole object or only a thin edge?',
    'curved': 'Which part can you describe: wall, rim, base or an incomplete curved edge?',
    'seam': 'Where does the raised seam run and end? Record it beside a scale.',
    'mark': 'What letters or numbers can you read exactly? Mark unreadable characters as unknown.',
    'glaze': 'Where can you already see the coating and the body beneath it? Compare both surfaces.',
    'grain': 'Are visible grains loose, joined together or interlocking? Describe their size and arrangement.',
    'layers': 'Do the bands continue through an existing edge or sit only on the surface?',
    'shell': 'What repeated ribs, spiral or outline can you see? Record shape without naming an organism.',
    'branch': 'Is the branching pattern a flat surface coating, an impression or a raised structure?',
    'holes': 'Are openings regular and repeated? Describe their edges without testing or cleaning them.',
    'rust': 'What outline remains visible through the corrosion? Photograph it without scraping.',
    'porous': 'Are the openings similar or varied? Show an existing surface without breaking the object.',
}
GUIDES = {
    'unknown': {
        'title': 'Start with what you can see', 'features': ['transparent','curved','mark','grain','layers','shell','branch','holes','porous'],
        'comparisons': ['A made object: look for a rim, joint, repeating manufactured shape or markings.',
                        'A natural material: record grains, crystals, layers and the surrounding rock.',
                        'A possible fossil: record the pattern and its relationship to the rock; resemblance alone is not identification.'],
        'questions': ['What does the object look like from both sides?', 'What is its size next to a ruler?',
                      'Are markings part of the object, or a coating on its surface?'],
        'source': ('NPS recognition examples','https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm')},
    'glass': {
        'title': 'Compare glass form and manufacturing clues', 'features': ['transparent','curved','seam','mark','holes'],
        'comparisons': ['Container fragment: look for a curved wall, base, neck or rim.',
                        'Flat glass: photograph the edges and thickness; shape alone does not establish its original use.',
                        'Natural glass or another shiny material: an irregular fragment needs expert comparison.'],
        'questions': ['Can you see a mold seam, and where does it end?', 'Are there raised letters or a base mark?',
                      'Which part is present: body, rim, neck, base, or only a fragment?'],
        'source': ('SHA / BLM historic bottle identification','https://secure-sha.org/bottle/')},
    'ceramic': {
        'title': 'Compare the body, surface and shape', 'features': ['curved','mark','glaze','grain','holes'],
        'comparisons': ['Vessel or dish fragment: look for a rim, foot, handle or decoration.',
                        'Brick or other building material: record the body and any regular faces or holes.',
                        'Natural rock resembling pottery: photograph an existing edge and surface; avoid breaking it to check.'],
        'questions': ['Does a coating differ from the exposed body?', 'Is there a maker’s mark or readable design?',
                      'Can the shape be described without guessing a date?'],
        'source': ('NPS ceramic recognition examples','https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm')},
    'metal': {
        'title': 'Compare the original shape and construction', 'features': ['curved','seam','mark','holes','rust'],
        'comparisons': ['Building hardware or fastener: record head, shaft and holes.',
                        'Container or sheet metal: record seams, joins and openings.',
                        'Unidentified corroded object: corrosion can hide the original shape.'],
        'questions': ['Are there joins, repeated holes or readable markings?', 'What parts of the outline remain visible?',
                      'Can you photograph it without scraping away the surface?'],
        'source': ('NPS metal recognition examples','https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm')},
    'rock': {
        'title': 'Describe rock texture before choosing a name', 'features': ['grain','layers','porous','branch','shell'],
        'comparisons': ['Grains or crystals: photograph their size, arrangement and variety.',
                        'Layers or bands: show how they pass through the object.',
                        'Coatings or inclusions: show the boundary with the surrounding material.'],
        'questions': ['Does it have one visible material or several?', 'Are grains loose, cemented, or interlocking?',
                      'Was it in transported gravel, or attached to a mapped rock exposure?'],
        'source': ('USGS rock types','https://pubs.usgs.gov/gip/acidrain/type.html')},
    'fossil': {
        'title': 'Compare biological structure with look-alikes', 'features': ['shell','branch','layers','grain','porous'],
        'comparisons': ['Possible preserved body or impression: photograph its outline and repeated structure.',
                        'Possible trace: show a track-like mark, burrow or trail and its surrounding rock.',
                        'Natural look-alike: mineral coatings, ripples and fractures can produce convincing patterns.'],
        'questions': ['Is the pattern three-dimensional, an impression, or only a surface coating?',
                      'Does the same structure continue into an existing edge?', 'What rock contains it, if that is known?'],
        'source': ('NPS fossil and look-alike guide','https://www.nps.gov/subjects/fossils/what-is-a-fossil.htm')},
    'bone': {
        'title': 'Preserve the context and ask an expert', 'features': ['porous','curved','grain'],
        'comparisons': ['A bone-like shape is an observation, not a species or age identification.',
                        'Rock and other materials may resemble bone; photos alone can be inconclusive.'],
        'questions': ['Can you record it in place without touching or moving it?',
                      'Can a qualified museum, archaeologist or local authority advise on the next step?'],
        'source': ('NPS bone recognition background','https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm')},
}


def inspect_find(material, features, setting, size, notes, *, town_context=None, state=None, geoid=None):
    if town_context is None:
        town_context = []
    if not isinstance(town_context, list) or town_context not in ([], ['town']):
        raise ValueError('Choose whether to include public town context.')
    place = get_place(geoid, state) if town_context else None
    if town_context and place is None:
        raise ValueError('Choose a matching public town before including town context.')
    if not isinstance(material, str) or material not in MATERIALS or not isinstance(setting, str) or setting not in SETTINGS:
        raise ValueError('Choose a material and where it was observed.')
    if not isinstance(features, list) or len(features) > 12 or any(not isinstance(f,str) or f not in GUIDES[material]['features'] for f in features):
        raise ValueError('Choose the visible features for this material.')
    for value, bound in ((size,80),(notes,1500)):
        if not isinstance(value,str) or len(value)>bound:
            raise ValueError('Keep size under 80 characters and observations under 1,500 characters.')
    guide = GUIDES[material]
    selected = list(dict.fromkeys(features))
    lines = [f"# {guide['title']}", '', '**Observation guide.** These comparisons are questions to investigate, not an identification or a date.', '',
             '## Your observations', '', f"- Material as described: {_md(MATERIALS[material])}.",
             f"- Setting: {_md(SETTINGS[setting])}.", f"- Size: {_md(size) if size.strip() else 'Not recorded'}.",
             '- Visible features: ' + (', '.join(_md(FEATURES[f]) for f in selected) if selected else 'None recorded yet') + '.', '']
    if place:
        lines += [f"Public town context: **{_md(place['name'])}, {_md(place['state'])}**. "
                  'Included by you as broad context; this is not an exact find location or verified provenance.', '']
    if notes.strip(): lines += ['**Notes:** ' + _md(notes), '']
    if material == 'bone':
        lines += ['**Leave it in place.** If human remains are possible, stop disturbing the area and contact local authorities. This guide cannot distinguish human from animal remains.', '']
    if selected:
        lines += ['## Questions for the features you noticed', '',
                  *['- ' + FEATURE_QUESTIONS[feature] for feature in selected], '']
    lines += ['## Compare these possibilities', '', *['- ' + item for item in guide['comparisons']], '',
              '## Look for these details next', '', *['- ' + item for item in guide['questions']], '']
    if 'branch' in selected:
        lines += ['A branching coating can be a mineral pattern. Branching shape by itself does not establish preserved plant material.', '']
    if 'seam' in selected and material == 'glass':
        lines += ['Photograph the seam through the neck and rim if present. Seam height alone is not a reliable bottle-date rule.', '']
    if setting == 'fill':
        lines += ['Imported fill separates the object from its original location. Town geology cannot establish where it came from.', '']
    lines += ['## Make a useful photo record', '',
              'Photograph the whole object, both sides and important details beside a ruler. Use steady light and a plain background when that can be done without moving a find. Keep an in-place context photograph. Do not scrape, break or chemically test an uncertain find for this guide.', '',
              f"[{guide['source'][0]}]({guide['source'][1]}). Use the guide to compare features and prepare questions for a museum or geological survey. "
              "The NPS examples come from a park context; its collecting rules are not a permission determination for another location.", '',
              '**Still unknown:** exact identity, age, provenance, ownership and collection rights. Record an expert opinion separately from these observations.', '']
    return {'material':material,'features':selected,'setting':setting,'size':size,'notes':notes,
            'place': f"{place['name']}, {place['state']}" if place else '',
            'markdown':'\n'.join(lines),'title':guide['title']}
