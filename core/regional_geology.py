"""Bounded, opt-in Macrostrat lookup at a public Census representative point."""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
import json
import re
from threading import Lock
from time import monotonic
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

API = "https://macrostrat.org/api/v2/geologic_units/map"
MAX_BYTES = 1_000_000
_CACHE = OrderedDict()
_LOCK = Lock()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise URLError("Provider redirect disabled")


def _text(value, limit=800):
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def parse_geology(payload):
    """Keep original map IDs and references; never combine maps into confidence."""
    success = payload.get("success") if isinstance(payload, dict) else None
    if not isinstance(success, dict) or success.get("license") != "CC-BY 4.0":
        raise ValueError("Unexpected provider schema or license")
    data, refs = success.get("data"), success.get("refs", {})
    if not isinstance(data, list) or len(data) > 100 or not isinstance(refs, dict):
        raise ValueError("Unexpected map units")
    units, seen = [], set()
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("Invalid map unit")
        map_id, source_id = row.get("map_id"), row.get("source_id")
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
               for value in (map_id, source_id)):
            raise ValueError("Invalid map identity")
        if map_id in seen:
            continue
        seen.add(map_id)
        original_reference = refs.get(str(source_id))
        if not isinstance(original_reference, str) or len(original_reference) > 1_600:
            raise ValueError("Original reference is missing or exceeds the reviewed length")
        reference = _text(original_reference, 1_600)
        if not reference:
            raise ValueError("Map unit has no original reference")
        units.append({"map_id": map_id, "source_id": source_id,
                      "name": _text(row.get("name"), 200) or "Unnamed map unit",
                      "lithology": _text(row.get("lith"), 400),
                      "description": _text(row.get("descrip"), 1_200),
                      "interval": _text(row.get("best_int_name"), 120),
                      "reference": reference})
    return units


def _request(latitude, longitude):
    # Inputs come exclusively from the bundled town lookup, not browser URLs.
    url = f"{API}?lat={latitude:.6f}&lng={longitude:.6f}"
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    request = Request(url, headers={"User-Agent": "Clovis/0.2 regional-context", "Accept": "application/json"})
    started = monotonic()
    with opener.open(request, timeout=6) as response:
        if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Unexpected provider response")
        chunks, size = [], 0
        while True:
            chunk = response.read(16_384)
            size += len(chunk)
            if size > MAX_BYTES or monotonic() - started > 12:
                raise ValueError("Provider response exceeds bounds")
            if not chunk:
                break
            chunks.append(chunk)
    return json.loads(b"".join(chunks).decode("utf-8"))


def geology_for_place(place):
    """Cache at most 128 public town requests in memory for an hour.

    A single nonblocking gate avoids queues of slow external requests. No
    coordinates or response data are written to disk by the application.
    """
    key = place["geoid"]
    if not _LOCK.acquire(blocking=False):
        return {"status": "unavailable", "units": [], "checked_at": "",
                "message": "Another geology lookup is running. Try again shortly."}
    try:
        cached = _CACHE.get(key)
        if cached and monotonic() - cached[0] < 3_600:
            _CACHE.move_to_end(key)
            return json.loads(json.dumps(cached[1]))
        checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            units = parse_geology(_request(place["latitude"], place["longitude"]))
            result = {"status": "available" if units else "no_coverage", "units": units,
                      "checked_at": checked_at, "message": "" if units else "No map unit was returned at this town point."}
        except (URLError, OSError, ValueError, UnicodeError, RecursionError):
            result = {"status": "unavailable", "units": [], "checked_at": checked_at,
                      "message": "Regional geology is unavailable. This is a data gap, not evidence of no finds."}
        # Short failure caching limits repeated requests without hiding recovery.
        cached_time = monotonic() if result["status"] != "unavailable" else monotonic() - 3_540
        _CACHE[key] = (cached_time, result)
        _CACHE.move_to_end(key)
        while len(_CACHE) > 128:
            _CACHE.popitem(last=False)
        return json.loads(json.dumps(result))
    finally:
        _LOCK.release()
