"""Small sourced routes from familiar words to literal Atlas searches.

An idea is a separate search the reader chooses. It never expands a query,
identifies an object, changes a filter, or adds terms to source records.
"""
from copy import deepcopy
import hashlib
import re
import unicodedata

GLOSSARY = 'https://www.nps.gov/subjects/archeology/glossary.htm'
ENVIRONMENT = 'https://historicengland.org.uk/images-books/publications/environmental-archaeology-3rd/heag327c-environmental-archaeology-appdx2/'
MAX_CHOICES = 6

# These are related routes, not equivalence assertions or identification rules.
# Terms are checked against the local catalogs in the dated search-workflow QA.
TOPICS = (
    {'id':'bottles', 'title':'Glass bottles',
     'cues':('bottle','bottles','old glass','pontil','mold seam','mould seam','mold seams','mould seams'),
     'queries':('glass bottle','pontil','mold seam'),
     'meaning':'Pontil scars and mold seams are manufacturing features discussed in bottle guides. Read several features together before interpreting an object.',
     'source_title':'NPS Yosemite artifact pocket guide',
     'source_url':'https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm'},
    {'id':'pottery', 'title':'Pottery pieces',
     'cues':('pot','pots','pottery','ceramic','ceramics','sherd','sherds','pot shard','pot shards'),
     'queries':('pottery','sherd','ceramic'),
     'meaning':'Archaeological descriptions use sherd for a broken ceramic piece. Pottery and ceramic searches can include whole vessels as well as fragments.',
     'source_title':'NPS archeology glossary', 'source_url':GLOSSARY},
    {'id':'points', 'title':'Stone points',
     'cues':('arrowhead','arrowheads','arrow head','arrow heads','spearhead','spearheads','projectile point','projectile points','dart point'),
     'queries':('projectile point','arrowhead'),
     'meaning':'Projectile point is a catalog term for a hafted stone point. A shape or keyword alone does not establish an object\'s function.',
     'source_title':'NPS projectile point and context',
     'source_url':'https://www.nps.gov/articles/projectile-point.htm'},
    {'id':'stone', 'title':'Stone and stone tools',
     'cues':('stone tool','stone tools','chipped stone','flint','lithic','lithics','knapping','flake','flakes','debitage'),
     'queries':('lithic','stone tool','flake'),
     'meaning':'Lithic is used for stone. Flake can describe a fragment produced during stone working; a broken stone still needs its recorded features and context examined.',
     'source_title':'NPS archeology glossary', 'source_url':GLOSSARY},
    {'id':'plants', 'title':'Burnt seeds and plant remains',
     'cues':('burnt seed','burnt seeds','burned seed','burned seeds','burnt grain','charred','carbonised seed','carbonized seed','flotation','archaeobotany'),
     'queries':('charred seeds','charred plant remains','flotation'),
     'meaning':'Charred plant material includes seeds and grains. Flotation describes a recovery process, while charred describes preservation; these searches ask different questions.',
     'source_title':'Historic England environmental remains, sections 1–2', 'source_url':ENVIRONMENT},
    {'id':'bones', 'title':'Animal bones',
     'cues':('animal bone','animal bones','bone fragment','bone fragments','faunal','fauna','zooarchaeology','zooarchaeological'),
     'queries':('animal bone','fauna','zooarchaeology'),
     'meaning':'Animal-remains studies cover different anatomical elements and animal groups. Read the recorded taxon and element separately; a word match does not identify a bone.',
     'source_title':'Historic England environmental remains, animal-remains sections', 'source_url':ENVIRONMENT},
    {'id':'layers', 'title':'Layers and contexts',
     'cues':('soil layer','soil layers','stratigraphy','stratum','strata','deposit','deposits','context','contexts'),
     'queries':('stratigraphy','deposit','context'),
     'meaning':'Stratigraphy concerns relationships among layers and contexts. Keep a layer\'s original project identity when comparing similarly named records.',
     'source_title':'NPS archeology glossary', 'source_url':GLOSSARY},
)


def _valid(query):
    return (isinstance(query,str) and len(query)<=120
            and not any(ord(char)<32 or 0xD800<=ord(char)<=0xDFFF for char in query))


def _words(text):
    return tuple(re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',text).casefold()))


def _contains(words, phrase):
    wanted=_words(phrase)
    return any(words[index:index+len(wanted)]==wanted for index in range(len(words)-len(wanted)+1))


def ideas(query):
    """Return bounded authored suggestions without touching any collection."""
    if not _valid(query):
        return {'topics':[], 'choices':[]}
    words=_words(query)
    if not query.strip():
        topics=TOPICS[:3]
    else:
        topics=tuple(topic for topic in TOPICS if any(_contains(words,cue) for cue in topic['cues']))[:3]
    origin=hashlib.sha256(query.encode('utf-8')).hexdigest()[:16]
    groups=[]
    for topic in topics:
        queries=topic['queries'][:1] if not query.strip() else topic['queries']
        group=[]
        for index,target in enumerate(queries):
            if _words(target)==words:
                continue
            group.append({'id':origin+':'+topic['id']+':'+str(index),'query':target})
        groups.append(group)
    choices=[group[index] for index in range(max(map(len,groups),default=0))
             for group in groups if index<len(group)][:MAX_CHOICES]
    return {'topics':deepcopy(list(topics)), 'choices':choices}


def chosen_query(query, identifier):
    """Only accept a currently offered authored choice, including its origin."""
    if not isinstance(identifier,str):
        return None
    return next((row['query'] for row in ideas(query)['choices'] if row['id']==identifier),None)
