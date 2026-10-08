"""Real bundled historical records and sourced statewide learning context."""
from core.sanborn_catalog import catalog_stats, census_town, search_catalog
from core.state_fossil_library import state_reading
from core.resident_context import _md
from core.usgs_unit_library import units_for_place
from core.newspaper_catalog import catalog_stats as newspaper_stats, search_titles
import sqlite3


def knowledge_for_place(place):
    state=place['state']
    town=census_town(place['name'])
    stats=catalog_stats(state,town)
    regional=catalog_stats(state)
    records=search_catalog(state,town,page=0,scope='town',order='oldest')
    chapter=state_reading(state)
    try:
        news=newspaper_stats(state,town)
        news_records=search_titles(state,town)['rows'][:3] if news['titles'] else []
    except (OSError,sqlite3.Error):
        news,news_records=None,[]
    return {'maps':stats,'regional_maps':regional,'records':records['results'][:3],
            'record_scope':records['scope'],'chapter':chapter,'usgs_units':units_for_place(place['geoid']),
            'newspapers':news,'newspaper_records':news_records}


def knowledge_markdown(place):
    knowledge=knowledge_for_place(place)
    stats=knowledge['maps']
    regional=knowledge['regional_maps']
    lines=[]
    units=knowledge.get('usgs_units',[])
    if units:
        lines+=['## Offline regional geology','',
                'USGS Cooperative National Geologic Map v2 (2026), 1:500,000 scale. These separate themes intersect the public Census town point; they are not a measured soil profile.','']
        for unit in units:
            lines+=[f"### {_md(unit['name'])}",f"Map theme: {_md(unit['layer_label'])}"]
            for key,label in (('age','Age'),('geomaterial','Geomaterial'),('description','National unit description')):
                if unit.get(key):
                    lines.append(f"{label}: {_md(unit[key])}")
            for source in unit.get('source_units',[])[:3]:
                lines+=['',f"**Recorded source unit: {_md(source.get('source_name') or source.get('source_mapunit') or '')}**"]
                if source.get('source_description'):
                    lines.append(_md(source['source_description']))
                if not source.get('source_name') and not source.get('source_full_name'):
                    lines.append('The USGS source table does not provide a description for this mapped source code.')
                for citation in source.get('source_citations',[])[:3]:
                    lines.append(_md(citation.get('text',''))+' '+_md(citation.get('url','')))
            if len(unit.get('source_units',[]))>3:
                lines.append('Open Mapped geology for the remaining source units and descriptions.')
            lines.append('')
        lines+=['[USGS national map and release](https://ngmdb.usgs.gov/Prodesc/proddesc_118545.htm)','']
    lines+=['## Dated historical sources','']
    if stats['maps']:
        span=''
        if stats.get('earliest') and stats.get('latest'):
            span=f" · {_md(stats['earliest'])} to {_md(stats['latest'])}"
        lines.append(f"**{stats['maps']:,} Sanborn map editions indexed to {_md(place['name'])}{span}.** Open Old maps to browse the dated catalog and inspect available sheets.")
    elif regional['maps']:
        lines.append(f"**{regional['maps']:,} Sanborn map editions from this state.** Open Old maps for the state catalog; this snapshot has no exact town-name match.")
    else:
        lines.append('This Sanborn snapshot has no indexed maps for this state or territory. Old maps retains live collection search and your own map viewer.')
    lines += ['', 'These fire-insurance records document buildings, construction materials and land use at their recorded dates. Check the sheet extent before comparing an individual place.', '']
    if knowledge['records']:
        lines.append('Cataloged town records:' if knowledge['record_scope']=='town' else 'State catalog examples:')
        for record in knowledge['records']:
            lines.append(f"- [{_md(record['title'])}]({record['url']}) · {_md(record['date'])}")
        lines.append('')
    lines += [f"[Library of Congress Sanborn collection and reuse rights]({stats['source_url']}) · Metadata snapshot {_md(stats['snapshot'])}", '']
    news=knowledge.get('newspapers')
    if news and news['titles']:
        lines+=['## Contemporary newspaper sources','',
                f"{news['titles']:,} title records indexed to this town in the partial LOC directory snapshot. The catalog records publication timelines, languages and holdings links; it contains no articles.",'']
        for record in knowledge['newspaper_records']:
            lines.append(f"- [{_md(record['title'])}]({record['url']}) · {_md(record.get('publication_dates',''))} · {_md(record.get('languages',''))}")
        lines+=['',f"Observed {news.get('source_pages_observed',0)} of {news.get('source_pages_expected',0)} directory pages. Additional titles may be on unharvested pages.",'']
    lines+=['## State geology and fossil story','']
    chapter=knowledge['chapter']
    if isinstance(chapter,dict):
        for fact in chapter.get('facts',[])[:5]:
            lines.append(fact['text'])
            sources=[f"[{_md(source['title'])}]({source['url']})" for source in fact.get('sources',[])[:5]]
            if sources:
                lines.append(' · '.join(sources))
            lines.append('')
    lines.append('Statewide context; these readings do not document a find at the selected town.')
    return knowledge,lines
