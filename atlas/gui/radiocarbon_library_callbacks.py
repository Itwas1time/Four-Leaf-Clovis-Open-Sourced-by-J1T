import sqlite3
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update
from core import radiocarbon_catalog as catalog
from core.fieldbook import EMPTY_BOOK, merge_entries
from atlas.gui.library_ui import reading_nav


def _age(value):
    if value is None:
        return None
    if type(value) not in (int, float) or not float(value).is_integer():
        raise ValueError("Use integer laboratory ages.")
    return int(value)


def _parameters(query, country, minimum, maximum):
    return {"query": query or "", "country": country or "all",
            "min_age": _age(minimum), "max_age": _age(maximum)}


@callback(Output("radiocarbon-country", "options"), Input("data-pack-refresh", "data"))
def countries(_refresh):
    try:
        return [{"label": "All recorded countries", "value": "all"}, *[
            {"label": f'{row["label"]} · {row["records"]:,}', "value": row["value"]} for row in catalog.definition()["countries"]]]
    except (ValueError, OSError, KeyError):
        return [{"label": "All recorded countries", "value": "all"}]


@callback(Output("radiocarbon-cards", "children"), Output("radiocarbon-count", "children"),
          Output("radiocarbon-page", "data"), Output("radiocarbon-page-label", "children"),
          Output("radiocarbon-previous", "disabled"), Output("radiocarbon-next", "disabled"),
          Output("radiocarbon-coverage", "children"),
          Input("radiocarbon-query", "value"), Input("radiocarbon-country", "value"),
          Input("radiocarbon-min-age", "value"), Input("radiocarbon-max-age", "value"),
          Input("radiocarbon-previous", "n_clicks"), Input("radiocarbon-next", "n_clicks"),
          Input("data-pack-refresh", "data"), State("radiocarbon-page", "data"))
def results(query, country, minimum, maximum, _previous, _next, _refresh, page):
    try:
        parameters = _parameters(query, country, minimum, maximum)
        page = page if type(page) is int and page >= 1 else 1
        trigger = callback_context.triggered_id
        page = max(1, page - 1) if trigger == "radiocarbon-previous" else page + 1 if trigger == "radiocarbon-next" else 1
        result = catalog.search(page=page, **parameters)
        if not result["installed"]:
            return [html.P("Install the world radiocarbon collection from Data collections to read and search these records.")], "Collection not installed", 1, "", True, True, catalog.definition()["coverage"]
        summary = catalog.stats()
        cards = [html.Button([html.Strong(row["lab_id"]),
                              html.Small(f'{row["age_bp"]:,} ± {row["error_bp"]:,} uncalibrated BP'),
                              html.Small(" · ".join(value for value in (row["material"], row["country"], row["site_name"]) if value))],
                             id={"type": "radiocarbon-open", "index": row["id"]}, n_clicks=0,
                             className="clovis-library-record") for row in result["rows"]]
        coverage = f'{summary["records"]:,} published determinations · source release {summary["source_release"]} · CC0. Uncalibrated laboratory ages; original one-sigma errors. Coordinates omitted.'
        return cards or [html.P("No dating results match these filters.")], f'{result["total"]:,} matching dating results', result["page"], f'{result["page"]} of {result["pages"]}', result["page"] <= 1, result["page"] >= result["pages"], coverage
    except (ValueError, OSError, sqlite3.Error, TypeError) as error:
        message = str(error) if isinstance(error, ValueError) else "The collection could not be read. Check its installation in Data collections."
        return [], message, 1, "", True, True, ""


@callback(Output("radiocarbon-selected", "data"), Input({"type": "radiocarbon-open", "index": ALL}, "n_clicks"),
          Input("radiocarbon-query", "value"), Input("radiocarbon-country", "value"),
          Input("radiocarbon-min-age", "value"), Input("radiocarbon-max-age", "value"),
          Input("radiocarbon-page", "data"), Input("data-pack-refresh", "data"))
def select(clicks, query, country, minimum, maximum, page, _refresh):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return None
    try:
        parameters = _parameters(query, country, minimum, maximum)
        result = catalog.search(page=page, **parameters)
        identifier = trigger["index"]
        if any(row["id"] == identifier for row in result["rows"]):
            return {"id": identifier, "page": page, "parameters": parameters}
    except (ValueError, OSError, sqlite3.Error, TypeError):
        pass
    return None


def current(selected, query, country, minimum, maximum, page):
    parameters = _parameters(query, country, minimum, maximum)
    if not isinstance(selected, dict) or selected.get("parameters") != parameters or selected.get("page") != page:
        return None
    result = catalog.search(page=page, **parameters)
    identifier = selected.get("id")
    return catalog.get_date(identifier) if any(row["id"] == identifier for row in result["rows"]) else None


@callback(Output("radiocarbon-detail", "children"), Input("radiocarbon-selected", "data"),
          Input("radiocarbon-query", "value"), Input("radiocarbon-country", "value"),
          Input("radiocarbon-min-age", "value"), Input("radiocarbon-max-age", "value"),
          Input("radiocarbon-page", "data"), Input("data-pack-refresh", "data"))
def reader(selected, query, country, minimum, maximum, page, _refresh):
    try:
        row = current(selected, query, country, minimum, maximum, page)
        if row is None:
            return html.P("Choose a published determination to read its original fields.")
        summary = catalog.stats()
        return [reading_nav("radiocarbon-query"), html.H3(row["lab_id"]),
                html.P("Published laboratory result", className="atlas-help"),
                html.Dl([node for label, value in catalog.facts(row) for node in (html.Dt(label), html.Dd(value))], className="clovis-library-facts"),
                html.P("These ages are uncalibrated radiocarbon years. No calendar conversion is applied.", className="atlas-help"),
                html.Details([html.Summary("Source field qualifications"), html.P(summary["source_field_note"])]),
                html.P(summary["citation"]),
                html.A("Collection publication & methods", href=summary["citation_url"], target="_blank", rel="noopener noreferrer"),
                html.P("CC0 data · Source attribution retained · Coordinates omitted.", className="atlas-help"),
                html.Button("Save dating reference to fieldbook", id="radiocarbon-save", n_clicks=0, className="atlas-primary-button"),
                html.Div(id="radiocarbon-save-status", role="status", className="atlas-help")]
    except (ValueError, OSError, sqlite3.Error, TypeError):
        return html.P("Choose a result from the current installed collection search.")


@callback(Output("fieldbook-store", "data", allow_duplicate=True), Output("radiocarbon-save-status", "children"),
          Input("radiocarbon-save", "n_clicks"), State("radiocarbon-selected", "data"),
          State("radiocarbon-query", "value"), State("radiocarbon-country", "value"),
          State("radiocarbon-min-age", "value"), State("radiocarbon-max-age", "value"),
          State("radiocarbon-page", "data"), State("fieldbook-store", "data"), prevent_initial_call=True)
def save(clicks, selected, query, country, minimum, maximum, page, book):
    if not clicks:
        return no_update, no_update
    try:
        row = current(selected, query, country, minimum, maximum, page)
        if row is None:
            return no_update, "Choose a dating result from the current search."
        entry = catalog.reference_entry(row["id"])
        return merge_entries(EMPTY_BOOK if book is None else book, [entry]), "Dating reference saved with its original laboratory age, uncertainty and source."
    except (ValueError, OSError, sqlite3.Error, TypeError, UnicodeError):
        return no_update, "The reference could not be saved. Check the selected result and fieldbook capacity."
