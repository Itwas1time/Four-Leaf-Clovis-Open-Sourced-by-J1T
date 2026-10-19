"""Reviewed local source editions; no network or user-selected file paths."""
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
from html import escape
import json
from pathlib import Path
import re

from core.fieldbook import validate_book
from core.resident_context import _md

REFERENCE = 'nps-yosemite-artifacts'
SOURCE_URL = 'https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm'
ASSET = Path(__file__).resolve().parents[1]/'atlas/gui/assets/local-reference-nps-yosemite-20250925-6c068bf4.json'
ASSET_SHA256 = 'bd40897255f5c368b44b2cf4684949e221d21ecb84dd9eb5806482a6c70de94f'


@lru_cache(maxsize=1)
def _load():
    # Review JSON uses canonical LF; Git checkouts may use CRLF. This does not
    # normalize the separately retained original HTTP entity or its receipt.
    raw = ASSET.read_bytes().replace(b'\r\n',b'\n')
    if len(raw)>250_000 or hashlib.sha256(raw).hexdigest()!=ASSET_SHA256:
        raise ValueError('The bundled source edition differs from its reviewed copy.')
    article = json.loads(raw)
    if (article.get('schema')!=1 or article.get('id')!=REFERENCE or article.get('source_url')!=SOURCE_URL
            or hashlib.sha256(article['original_visible_text'].encode()).hexdigest()!=article['visible_text_sha256']):
        raise ValueError('The bundled source edition needs review.')
    return article


def get(identifier):
    if identifier != REFERENCE or not isinstance(identifier,str):
        return None
    try:
        return deepcopy(_load())
    except (OSError,ValueError,KeyError,TypeError):
        return None


def for_url(url):
    return get(REFERENCE) if isinstance(url,str) and url==SOURCE_URL else None


def reading_text(article):
    lines=[article['title'], '', article['publisher'], article['source_url'],
        'Source page updated: '+article['source_updated'],
        'Retrieved: '+article['receipt']['retrieved_utc'],
        'Original HTML SHA-256: '+article['receipt']['sha256'], '',
        article['scope'], article['content_note'], '', article['attribution'],
        article['rights_basis'], 'Source policy: '+article['policy_receipt']['url'], '']
    for block in article['blocks']:
        if block['type'] in ('heading','paragraph'):
            lines.extend([block['text'],''])
        elif block['type']=='list':
            lines.extend('- '+text for text in block['items'])
            lines.append('')
        elif block['type']=='figure-description':
            lines.extend(['Source illustration description: '+block['alt'],block['caption'],
                'Original image URL (image not bundled): '+block['source_image_url'],''])
    return '\n'.join(lines)


def reference_entry(identifier):
    article=get(identifier)
    if article is None:
        raise ValueError('The local source could not be read. Check the Clovis installation.')
    literal=lambda value:'\n'.join(_md(line) for line in value.split('\n'))
    markdown='# Government source reference\n\n'+literal(reading_text(article))
    markdown+='\n\n## Complete bundled source edition JSON\n\n'+literal(json.dumps(article,ensure_ascii=False,indent=2))
    row={'id':hashlib.sha256(('local-reference:'+identifier+markdown).encode()).hexdigest()[:24],
        'kind':'investigation', 'title':('NPS · '+article['title']).encode()[:120].decode('utf-8','ignore'),
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'mission':'Government source reference','source':article['publisher']+' · '+article['source_url'],
            'date':'Source page updated '+article['source_updated'],
            'outcome':'Publisher guidance; no object identified or observed'}, 'markdown':markdown}
    validate_book({'version':1,'entries':[row]})
    return row


def _anchor(text):
    return re.sub(r'[^a-z0-9]+','-',text.casefold()).strip('-')


def render_html(article):
    esc=escape
    title=esc(article['title'])
    parts=['<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>'+title+' · Clovis local source</title>',
        '<link rel="stylesheet" href="/assets/offline_reference.css"></head><body class="clovis-local-reference"><main>',
        '<p class="eyebrow">Clovis · Local source text</p><h1>'+title+'</h1>',
        '<p>'+esc(article['publisher'])+'</p><p class="scope">'+esc(article['scope'])+'</p>',
        '<p>'+esc(article['content_note'])+'</p>',
        '<nav aria-label="Source sections"><ul>']
    parts.extend('<li><a href="#'+_anchor(b['text'])+'">'+esc(b['text'])+'</a></li>'
        for b in article['blocks'] if b['type']=='heading' and b['level']==2)
    parts.extend(['</ul></nav>','<article aria-label="Original NPS article text">'])
    for block in article['blocks']:
        kind=block['type']
        if kind=='heading':
            level=str(block['level'])
            parts.append('<h'+level+' id="'+_anchor(block['text'])+'">'+esc(block['text'])+'</h'+level+'>')
        elif kind=='paragraph':
            parts.append('<p>'+esc(block['text'])+'</p>')
        elif kind=='list':
            tag='ol' if block['ordered'] else 'ul'
            parts.append('<'+tag+'>'+''.join('<li>'+esc(text)+'</li>' for text in block['items'])+'</'+tag+'>')
        elif kind=='figure-description':
            parts.append('<aside><strong>Source illustration description</strong><p>'+esc(block['alt'])+'</p><p>'+esc(block['caption'])+'</p></aside>')
    parts.extend(['</article><footer><h2>Source edition and attribution</h2>',
        '<p>Source page updated '+esc(article['source_updated'])+' · retrieved '+esc(article['receipt']['retrieved_utc'])+'</p>',
        '<p>'+esc(article['attribution'])+'</p><p>'+esc(article['rights_basis'])+'</p>',
        '<p>Original HTML SHA-256: <code>'+article['receipt']['sha256']+'</code></p>',
        '<p><a href="'+esc(article['source_url'],quote=True)+'" target="_blank" rel="noopener noreferrer">View current NPS page (online)</a></p>',
        '<p><a href="/reference/local/'+REFERENCE+'/text">Download this source text</a></p>',
        '<p>Return to your Clovis tab to keep investigating or save the complete source to your fieldbook.</p>',
        '</footer></main></body></html>'])
    return ''.join(parts)


def register_routes(server):
    from flask import Response

    @server.get('/reference/local/<identifier>')
    def local_source_page(identifier):
        article=get(identifier)
        if article is None:
            return Response('This local source is not available.',status=404,mimetype='text/plain')
        return Response(render_html(article),mimetype='text/html',headers={
            'Content-Security-Policy':"default-src 'none'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            'X-Content-Type-Options':'nosniff','Cache-Control':'public, max-age=3600'})

    @server.get('/reference/local/<identifier>/text')
    def local_source_text(identifier):
        article=get(identifier)
        if article is None:
            return Response('This local source is not available.',status=404,mimetype='text/plain')
        return Response(reading_text(article),mimetype='text/plain',headers={
            'Content-Disposition':'attachment; filename="clovis-nps-yosemite-source.txt"',
            'X-Content-Type-Options':'nosniff'})
