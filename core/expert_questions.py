"""Immutable, user-authored question and attributed response snapshots.

No identification, source verification, outreach or image processing occurs.
Records keep the existing fieldbook v1 schema and can be exported/imported.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import re
import unicodedata

from core.fieldbook import validate_book

QUESTION_MISSION = 'Expert question'
RESPONSE_MISSION = 'Expert response'
LIMITS = {'question': 1500, 'comparison': 1500, 'wanted_detail': 1500,
          'attribution': 200, 'response': 4000, 'remaining_uncertainty': 1500}


def _text(value, label, limit, *, required=False):
    if not isinstance(value, str):
        raise ValueError(f'{label} must be text.')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError:
        raise ValueError(f'{label} contains invalid Unicode.') from None
    if size > limit:
        raise ValueError(f'Shorten the {label} before saving.')
    if any(unicodedata.category(char).startswith('C') and char != '\n' for char in value):
        raise ValueError(f'{label} contains unsupported control or invisible characters.')
    value = value.strip()
    if required and not value:
        raise ValueError(f'Write {label}.')
    return value


def _escaped(value):
    # Preserve line breaks while disabling user-controlled Markdown and HTML.
    return re.sub(r'([\\`*_{}\[\]<>()!#|~+\-.=])', r'\\\1', value)


def _snapshot(row):
    try:
        validate_book({'version': 1, 'entries': [row]})
        copied = deepcopy(row)
        for key in ('title', 'created', 'markdown'):
            _text(copied[key], 'Saved ' + key, 100_000, required=True)
        for value in copied['summary'].values():
            _text(value, 'Saved comparison field', 1500)
    except (ValueError, TypeError, UnicodeError, RecursionError, KeyError):
        raise ValueError('Choose valid saved fieldbook notes before preparing a question or response.') from None
    return copied


def _entry(parent, mission, title, summary, addition):
    original_fields = '\n'.join('- ' + _escaped(key) + ': ' + _escaped(value)
                                for key, value in sorted(parent['summary'].items()))
    markdown = (parent['markdown'] + '\n\n### Preserved saved snapshot fields\n\n'
                + 'Parent record: ' + parent['id'] + '\n\n'
                + 'Original title: ' + _escaped(parent['title']) + '\n\n'
                + 'Original record kind: ' + parent['kind'] + '\n\n'
                + 'Original saved UTC time: ' + parent['created'] + '\n\n' + original_fields
                + '\n\n' + addition)
    row = {'id': hashlib.sha256((mission + '\n' + parent['id'] + '\n' + markdown).encode('utf-8')).hexdigest()[:24],
           'kind': 'investigation',
           'title': title.encode('utf-8')[:120].decode('utf-8', 'ignore'),
           'created': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           'summary': summary, 'markdown': markdown}
    validate_book({'version': 1, 'entries': [row]})
    return row


def prepare_question(row, question, comparison, wanted_detail):
    """Append a question to a copied snapshot; repeated content deduplicates.

    Broad town context is copied only if already present in the saved summary.
    Comparison/detail may be blank; the question must be nonempty.
    """
    parent = _snapshot(row)
    if parent['summary'].get('mission') in (QUESTION_MISSION, RESPONSE_MISSION):
        raise ValueError('Choose the original saved observation to prepare another question.')
    question = _text(question, 'question', LIMITS['question'], required=True)
    comparison = _text(comparison, 'comparison', LIMITS['comparison'])
    wanted_detail = _text(wanted_detail, 'wanted detail', LIMITS['wanted_detail'])
    summary = dict(parent['summary'])
    summary.update(mission=QUESTION_MISSION, source='Saved observation: ' + parent['id'],
                   outcome='Question prepared; no response recorded', follow_up=question,
                   steps=wanted_detail or 'Not recorded')
    addition = '\n'.join([
        '## Your expert question', '',
        'User-prepared question; Clovis has not identified the object or contacted anyone.', '',
        '**Question:** ' + _escaped(question), '',
        '**Possible interpretation to compare:** ' + (_escaped(comparison) if comparison else 'Not recorded'),
        'This is a proposed interpretation, not an observed fact or verified identification.', '',
        '**Detail you want help with:** ' + (_escaped(wanted_detail) if wanted_detail else 'Not recorded'), '',
        '### Photo checklist for your question', '',
        '- Whole object and both sides, when these can be recorded without moving it.',
        '- A scale and a close view of the feature named in your question.',
        '- An in-place context view where available; omit personal details and precise sensitive locations.',
        'No photograph is embedded or attached to this record. The checklist does not authorize handling or collection.', '',
        'Identity, age and find likelihood remain unestablished by this question.',
    ])
    return _entry(parent, QUESTION_MISSION, 'Question · ' + parent['title'], summary, addition)


def response_entry(row, attribution, response_date, response, remaining_uncertainty):
    """Record a response separately; author attribution is user-recorded.

    response_date is the stated response date (YYYY-MM-DD), independent of the
    UTC time this new snapshot is created. Earlier documented dates are valid.
    """
    parent = _snapshot(row)
    if parent['kind'] != 'investigation' or parent['summary'].get('mission') != QUESTION_MISSION:
        raise ValueError('Choose a saved expert question before recording a response.')
    attribution = _text(attribution, 'attribution', LIMITS['attribution'], required=True)
    response_date = _text(response_date, 'response date', 10, required=True)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', response_date):
        raise ValueError('Use a response date in YYYY-MM-DD format.')
    try:
        date.fromisoformat(response_date)
    except ValueError:
        raise ValueError('Use a valid calendar response date.') from None
    response = _text(response, 'response', LIMITS['response'], required=True)
    remaining_uncertainty = _text(remaining_uncertainty, 'remaining uncertainty', LIMITS['remaining_uncertainty'])
    summary = dict(parent['summary'])
    summary.update(mission=RESPONSE_MISSION, source=attribution, date=response_date,
                   outcome='User-recorded response; not independently verified',
                   follow_up=remaining_uncertainty or 'Not recorded')
    addition = '\n'.join([
        '## Your recorded expert response', '',
        'This response and attribution were recorded by the user. Clovis has not contacted the named source, verified credentials, or independently checked the response.', '',
        '**Attributed to:** ' + _escaped(attribution), '',
        '**Stated response date:** ' + response_date, '',
        '**Recorded response:** ' + _escaped(response), '',
        '**Remaining uncertainty:** ' + (_escaped(remaining_uncertainty) if remaining_uncertainty else 'Not recorded; absence of a note does not resolve uncertainty.'), '',
        'The original observations and question are preserved in this record. A recorded response is separate from an app conclusion.',
    ])
    return _entry(parent, RESPONSE_MISSION, 'Response · ' + parent['title'], summary, addition)


def question_first_markdown(row):
    """Lead with the question/response for reading; stored snapshots stay intact."""
    validate_book({'version':1, 'entries':[row]})
    header = {QUESTION_MISSION:'## Your expert question',
              RESPONSE_MISSION:'## Your recorded expert response'}.get(row['summary'].get('mission'))
    if header is None:
        return row['markdown']
    original, separator, current = row['markdown'].rpartition('\n\n' + header + '\n')
    if not separator:
        return row['markdown']
    return header + '\n' + current + '\n\n## Preserved source notes\n\n' + original
