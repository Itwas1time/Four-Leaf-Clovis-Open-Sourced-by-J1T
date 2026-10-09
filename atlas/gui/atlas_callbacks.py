"""Common local search, authoritative record reading and evidence navigation."""
import sqlite3
from urllib.parse import urlsplit
from dash import ALL, MATCH, Input, Output, State, callback, callback_context, html, no_update
from core import atlas_catalog as catalog, excavation_catalog, environment_catalog, zooarchaeology_catalog
from core.fieldbook import EMPTY_BOOK, merge_entries
from core.data_packs import PackStore
from atlas.gui.library_ui import reading_nav
from atlas.gui.published_location_ui import control as location_control, render as location_map

ERRORS = (ValueError, OSError, sqlite3.Error, TypeError, KeyError)
PACK_SOURCES = {"radiocarbon-world": "dates", "dinosaur-sites": "dinosaurs", "neolithic-assemblages": "assemblages",
                "excavations-surveys": "contexts", "dated-environments": "environments", "anatolian-zooarchaeology": "specimens"}


@callback(Output("library-section", "value", allow_duplicate=True),
          Input("atlas-return", "n_clicks"), Input("atlas-manage-packs", "n_clicks"), prevent_initial_call=True)
def navigate(_return, _manage):
    return "packs" if callback_context.triggered_id == "atlas-manage-packs" else "atlas"


@callback(Output("resident-tool", "value", allow_duplicate=True), Input("header-place-button", "n_clicks"),
          State("resident-tool", "value"), prevent_initial_call=True)
def choose_town(clicks, tool):
    return "map" if clicks and tool == "library" else no_update


def _parameters(query, kind, source, context):
    return {"query": query or "", "kind": kind or "all", "source": source or "all",
            "context": context.get("parameters") if isinstance(context, dict) else None}


def _source_link(url, label):
    try:
        parsed = urlsplit(url)
        if (isinstance(url, str) and len(url) <= 2000 and parsed.scheme == "https" and parsed.hostname
                and not parsed.username and not parsed.password and parsed.port in (None, 443)
                and not any(ord(char) < 33 for char in url)):
            return html.A(label, href=url, target="_blank", rel="noopener noreferrer")
    except (ValueError, TypeError):
        pass
    return None


@callback(Output("atlas-cards", "children"), Output("atlas-count", "children"), Output("atlas-page", "data"),
          Output("atlas-page-label", "children"), Output("atlas-previous", "disabled"), Output("atlas-next", "disabled"),
          Output("atlas-coverage", "children"), Output("atlas-context-label", "children"), Output("atlas-context-banner", "style"),
          Input("atlas-query", "value"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          Input("atlas-context", "data"), Input("atlas-previous", "n_clicks"), Input("atlas-next", "n_clicks"),
          Input("data-pack-refresh", "data"), State("atlas-page", "data"))
def results(query, kind, source, context, _previous, _next, _refresh, page):
    try:
        page = page if type(page) is int and page >= 1 else 1
        trigger = callback_context.triggered_id
        page = max(1, page - 1) if trigger == "atlas-previous" else page + 1 if trigger == "atlas-next" else 1
        result = catalog.search(page=page, **_parameters(query, kind, source, context))
        cards = [html.Button([html.Small(row["evidence"], className="clovis-atlas-evidence"),
                              html.Strong(row["title"]), html.Small(row["subtitle"]), html.Small(row["source_label"])],
                             id={"type": "atlas-open", "index": row["id"]}, n_clicks=0,
                             className="clovis-library-record") for row in result["rows"]]
        coverage = [html.P("Records include different evidence types. Counts describe source records; observations may overlap between collections.", className="atlas-help"),
                    html.Ul([html.Li(f'{row["label"]}: {row["records"]:,} matching records') for row in result["coverage"]])]
        if result["missing"]:
            coverage.append(html.Ul([html.Li(row["label"] + ": " + row["reason"]) for row in result["missing"]]))
        label = f'{result["total"]:,} matching source records'
        if result["missing"]:
            label += f' · {len(result["missing"])} collection(s) unavailable; see Search coverage'
        return (cards or [html.P("No records match. Try a shorter name or broaden the evidence or source.")], label,
                result["page"], f'{result["page"]:,} of {result["pages"]:,}', result["page"] <= 1,
                result["page"] >= result["pages"], coverage,
                context.get("label", "Associated source evidence") if isinstance(context, dict) else "",
                {} if context else {"display": "none"})
    except ERRORS as error:
        return [], str(error) if isinstance(error, ValueError) else "The atlas could not read this search. Check offline collections.", 1, "", True, True, [], "", {"display": "none"}


@callback(Output("atlas-selected", "data"), Input({"type": "atlas-open", "index": ALL}, "n_clicks"),
          Input("atlas-query", "value"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          Input("atlas-context", "data"), Input("atlas-page", "data"), Input("data-pack-refresh", "data"))
def select(clicks, query, kind, source, context, page, _refresh):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return None
    try:
        parameters = _parameters(query, kind, source, context)
        result = catalog.search(page=page, **parameters)
        identifier = trigger["index"]
        if any(row["id"] == identifier for row in result["rows"]):
            return {"id": identifier, "page": page, "parameters": parameters}
    except ERRORS:
        pass
    return None


def current(selected, query, kind, source, context, page):
    parameters = _parameters(query, kind, source, context)
    if not isinstance(selected, dict) or selected.get("parameters") != parameters or selected.get("page") != page:
        return None
    result = catalog.search(page=page, **parameters)
    identifier = selected.get("id")
    return catalog.get_record(identifier) if any(row["id"] == identifier for row in result["rows"]) else None


def _facts(rows):
    return html.Dl([node for label, value in rows for node in (html.Dt(label), html.Dd(value))], className="clovis-library-facts")


def _reading_facts(record):
    if record["source"] != "specimens":
        return record["facts"]
    names = {"Published context": "Context", "Related person(s)": "Contributors",
             "Has Biological Taxonomy [Label]": "Published taxon",
             "Has Biological Taxonomy [Source value]": "Recorded taxon",
             "Has anatomical identification [Label]": "Anatomical element",
             "Has anatomical identification [Source value]": "Recorded element"}
    rows = []
    for label, value in record["facts"]:
        # Exact source terms, ontology URIs and full provenance remain in the
        # original edition panels and saved reference.
        if label == "Source edition" or label.endswith(" [URI]"):
            continue
        header, separator, table = label.partition(" · ")
        if separator:
            label = header.removesuffix(" [Source]") + " · " + table.rsplit("/", 1)[-1]
        rows.append((names.get(label, label), value))
    return rows


@callback(Output("atlas-detail", "children"), Input("atlas-selected", "data"),
          Input("atlas-query", "value"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          Input("atlas-context", "data"), Input("atlas-page", "data"), Input("data-pack-refresh", "data"))
def reader(selected, query, kind, source, context, page, _refresh):
    try:
        row = current(selected, query, kind, source, context, page)
        if row is None:
            return html.P("Choose a result to read its evidence, context and source.")
        children = [reading_nav("atlas-query"), html.P(row["evidence"], className="clovis-atlas-evidence"),
                    html.H3(row["title"]), html.P(row["source_label"], className="atlas-help"), _facts(_reading_facts(row))]
        if row["description"]:
            children.append(html.P(row["description"]))
        links = catalog.relationships(row)
        if links:
            def button(link):
                return html.Button(f'{link["total"]:,} · {link["label"]}',
                                   id={"type": "atlas-related", "index": link["key"]},
                                   n_clicks=0, className="atlas-secondary-button")
            main_keys = ("animals", "plants", "dates", "phases", "sites", "parent", "children", "source-rows", "subject")
            main = [link for link in links if link["key"] in main_keys or
                    row["source"] == "environments" and link["parameters"]["view"] in ("observation", "sample", "age", "date")][:4]
            more = [link for link in links if link not in main]
            children.append(html.Div([html.H4("Associated evidence"), *[button(link) for link in main]], className="clovis-atlas-related"))
            if more:
                children.append(html.Details([html.Summary("More associated evidence"),
                    html.Div([button(link) for link in more], className="clovis-atlas-related")]))
        if row["source"] == "specimens":
            original = row["original"]
            editions = original["editions"]
            if original["kind"] == "context":
                representative = original["representative"]
                fields = [(header, zooarchaeology_catalog.value_text(value))
                          for header, value in zip(representative["headers"], representative["values"])
                          if header.startswith("Context (") or header in ("Context URI", "Project URI", "Project name", "Related person(s)")]
                children.append(html.Details([html.Summary("Original context reference"), _facts(fields),
                    html.P("These fields come from a specimen table row. Read the linked original rows for the separately recorded specimens and measurements.", className="atlas-help"),
                    _source_link(representative["table"]["source_url"], "Read this original source table")]))
            for edition in editions:
                table = edition["table"]
                children.append(html.Details([html.Summary(table["path"] + " · row " + str(edition["ordinal"])),
                    html.P("Original table SHA-256: " + table["sha256"], className="atlas-help"),
                    _facts(edition["fields"]), _source_link(table["source_url"], "Read original source table")]))
        elif row["source"] == "environments":
            original = row["original"]
            text = environment_catalog.value_text
            children.append(html.Details([html.Summary("Original source fields"),
                                         _facts((key, text(value)) for key, value in original["source"].items())]))
            context_fields = [(key, values) for key, values in original["associated"].items()
                              if key in ("sample", "dataset", "analysis", "chronology") and values]
            if context_fields:
                children.append(html.Details([html.Summary("Sample and collection context"),
                    *[html.Details([html.Summary(key.capitalize()), _facts((name, text(value)) for name, value in values.items())]) for key, values in context_fields]]))
            locations = environment_catalog.location_fields(original)
            if locations:
                children.append(html.Details([html.Summary("Published location"), location_control(row["id"]), *[_facts(fields) for fields in locations]]))
            if original["age_assignments"]:
                models = []
                for assignment in original["age_assignments"]:
                    chronology = assignment["chronology"]
                    models.append(html.Details([html.Summary(chronology.get("chronologyname") or "Chronology " + str(assignment["source"]["chronologyid"])),
                        _facts((key, text(value)) for key, value in assignment["source"].items()),
                        _facts((key, text(value)) for key, value in chronology.items()),
                        _facts((key, text(value)) for key, value in assignment["age_type"].items())]))
                children.append(html.Details([html.Summary(f'{original["age_assignments_total"]:,} sample age assignments'), *models,
                    html.P("These are age assignments from the original models. Dating measurements remain separate.", className="atlas-help"),
                    *([html.P(f'Showing {len(models):,} of {original["age_assignments_total"]:,} assignments. Open the associated age evidence to read the others.', className="atlas-help")]
                      if original["age_assignments_total"] > len(models) else [])]))
            meanings = [(key, values) for key, values in original["associated"].items()
                        if key in ("variable", "taxon", "variable_units", "element", "variable_context", "control_type", "date_type") and values]
            if meanings or original["uncertainties"] or original.get("radiocarbon"):
                children.append(html.Details([html.Summary("Variable meanings and measurement details"),
                    *[html.Details([html.Summary(key.replace("_", " ").capitalize()), _facts((name, text(value)) for name, value in values.items())]) for key, values in meanings],
                    *[_facts((key, text(value)) for key, value in row.items()) for row in original["uncertainties"]],
                    *[_facts((key, text(value)) for key, value in meaning[group].items())
                      for meaning in original["uncertainty_meanings"] for group in ("unit", "basis")],
                    _facts((key, text(value)) for key, value in original.get("radiocarbon", {}).items())]))
            if original["publications"] or original["dataset_dois"]:
                children.append(html.Details([html.Summary("Source publications and dataset identifiers"),
                    *[html.Div([html.P(publication.get("citation") or "Publication " + publication["publicationid"]),
                        _facts((key, text(publication[key])) for key in ("publicationid", "articletitle", "booktitle", "year", "journal", "volume", "issue", "pages", "publisher", "doi", "url") if key in publication),
                        _source_link(publication.get("url"), "Read source publication")]) for publication in original["publications"]],
                    *[_facts((key, text(value)) for key, value in row.items()) for row in original["dataset_dois"]]]))
        elif row["source"] == "assemblages":
            original = row["original"]
            children.append(html.Details([html.Summary("Original source fields"), _facts(original["source"].items())]))
            for key, title in (("animal_recovery", "Animal recovery methods"), ("plant_sampling", "Plant sampling phase"),
                               ("plant_recovery", "Plant recovery methods")):
                fields = original["associated"].get(key)
                if fields:
                    children.append(html.Details([html.Summary(title), _facts(fields.items())]))
        elif row["source"] == "contexts":
            original = row["original"]
            locations = excavation_catalog.location_time_fields(original)
            if locations:
                children.append(html.Details([html.Summary("Published location and time"),
                    *[_facts(fields) for fields in locations],
                    html.P("Location references and precision retain the publisher's wording. Source ISO years use 0000 for 1 BCE.", className="atlas-help")]))
            for observation in original["observations"]:
                children.append(html.Details([html.Summary(observation.get("label", observation["id"])),
                    _facts(excavation_catalog.observation_fields(observation, original["definitions"]))]))
            if original["tables"]:
                children.append(html.Details([html.Summary("Original published table fields"), *[
                    html.Details([html.Summary(table["title"]),
                                  html.Dl([node for key, value in table["fields"].items() for node in
                                           (html.Dt(key.split(" [", 1)[0], title=key), html.Dd(value if value != "" else "Not recorded"))],
                                          className="clovis-library-facts"),
                                  _source_link(table["uri"], "Read source table")]) for table in original["tables"]]]))
            definitions = excavation_catalog.definition_fields(original)
            if definitions:
                children.append(html.Details([html.Summary("Field meanings and units"), *[
                    html.Div([html.H4(group["label"]), _facts(group["fields"]),
                              _source_link(group["source_uri"], "Read original field definition")]) for group in definitions]]))
        elif row["source"] == "dinosaurs":
            original = row["original"].get("source")
            if original:
                children.append(html.Details([html.Summary("Original occurrence fields"), _facts(original.items())]))
                children.append(html.Details([html.Summary("Published location"), location_control(row["id"])]))
        children += [html.Details([html.Summary("Evidence conventions"), *[html.P(note) for note in row["notes"]]]),
                     _source_link(row["source_url"], "Read original source"), html.P(row["license"], className="atlas-help"),
                     html.Button("Save source to fieldbook", id="atlas-save", n_clicks=0, className="atlas-primary-button"),
                     html.Div(id="atlas-save-status", role="status", className="atlas-help")]
        return children
    except ERRORS:
        return html.P("Choose a record from the current atlas search.")


@callback(Output({"type": "atlas-location-view", "index": MATCH}, "children"),
          Input({"type": "atlas-location-open", "index": MATCH}, "n_clicks"),
          State("atlas-selected", "data"), State("atlas-query", "value"), State("atlas-kind", "value"),
          State("atlas-source", "value"), State("atlas-context", "data"), State("atlas-page", "data"),
          State({"type": "atlas-location-open", "index": MATCH}, "id"),
          prevent_initial_call=True)
def published_map(clicks, selected, query, kind, source, context, page, button):
    if not clicks:
        return no_update
    try:
        row = current(selected, query, kind, source, context, page)
        if row is not None and isinstance(button, dict) and button.get("index") == row["id"]:
            return location_map(row)
    except ERRORS:
        pass
    return html.P("Choose a record from the current atlas search.", className="atlas-help")


@callback(Output("atlas-context", "data"), Output("atlas-query", "value", allow_duplicate=True),
          Input({"type": "atlas-related", "index": ALL}, "n_clicks"),
          Input("atlas-clear-context", "n_clicks"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          State("atlas-selected", "data"), State("atlas-query", "value"), State("atlas-context", "data"),
          State("atlas-page", "data"), prevent_initial_call=True)
def associated(clicks, _clear, kind, source, selected, query, context, page):
    trigger = callback_context.triggered_id
    if trigger in ("atlas-clear-context", "atlas-kind", "atlas-source"):
        return None, no_update
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return no_update, no_update
    try:
        row = current(selected, query, kind, source, context, page)
        if row:
            for link in catalog.relationships(row):
                if link["key"] == trigger["index"]:
                    # The originating search term need not occur in its linked deposit.
                    return {"parameters": link["parameters"], "label": row["title"] + " · " + link["label"]}, ""
    except ERRORS:
        pass
    return no_update, no_update


@callback(Output("atlas-source", "value"), Output("atlas-kind", "value"),
          Input({"type": "data-pack-open", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def open_pack(clicks):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return no_update, no_update
    identifier = trigger.get("index")
    try:
        if identifier in PACK_SOURCES and PackStore().status(identifier)["state"] == "installed":
            return PACK_SOURCES[identifier], "all"
    except ERRORS:
        pass
    return no_update, no_update


@callback(Output("fieldbook-store", "data", allow_duplicate=True), Output("atlas-save-status", "children"),
          Input("atlas-save", "n_clicks"), State("atlas-selected", "data"), State("atlas-query", "value"),
          State("atlas-kind", "value"), State("atlas-source", "value"), State("atlas-context", "data"),
          State("atlas-page", "data"), State("fieldbook-store", "data"), prevent_initial_call=True)
def save(clicks, selected, query, kind, source, context, page, book):
    if not clicks:
        return no_update, no_update
    try:
        row = current(selected, query, kind, source, context, page)
        if row is None:
            return no_update, "Choose a record from the current search."
        entry = catalog.reference_entry(row["id"])
        return merge_entries(EMPTY_BOOK if book is None else book, [entry]), "Source reference saved to fieldbook."
    except (*ERRORS, UnicodeError):
        return no_update, "The source could not be saved. Check the selected record and fieldbook capacity."
