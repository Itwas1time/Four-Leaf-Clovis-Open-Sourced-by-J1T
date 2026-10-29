"""Start first-use work in the background when the server starts, off the person's path.

Installed collections are fully re-verified (SHA-256) on first use in every process; that
guarantee stays. Doing it at startup means the first town lookup and the first Atlas search no
longer wait for it (a cold first search took 13-23 s on 29 Oct 2026; prepared, 0.7 s).
A request that arrives during the warm-up shares the same per-file check instead of repeating it.
The landing page itself never triggers this work (see tests/test_atlas_landing_deferred.py).
"""
import sqlite3
from threading import Thread


def _prepare_town_names():
    # Every typed Atlas query is also checked against US town names; building that index on
    # the first query (0.3-0.6 s) competed with the first search on 29 Oct 2026.
    from core import us_places
    try:
        us_places._places_by_base_name()
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        pass


def _verify_collections():
    from core import nearby_records
    try:
        nearby_records._databases()
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        pass  # best effort: real requests verify again and report any problem to the person


def _prepare_search():
    # The same verified preparation as "Prepare all sources"; its result is never served
    # directly, and every real search still checks each collection's signature.
    from core import atlas_catalog
    try:
        atlas_catalog.search()
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        pass


def _run():
    _prepare_town_names()
    _verify_collections()
    _prepare_search()


def start():
    thread = Thread(target=_run, name='clovis-warmup', daemon=True)
    thread.start()
    return thread
