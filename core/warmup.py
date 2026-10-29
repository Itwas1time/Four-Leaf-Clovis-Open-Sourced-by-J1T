"""Start first-use work in the background when the server starts, off the person's path.

Installed collections are fully re-verified (SHA-256) on first use in every process; that
guarantee stays. Doing it at startup means the first town lookup no longer waits ~5 s for it.
A request that arrives during the warm-up shares the same per-file check instead of repeating it.
"""
import sqlite3
from threading import Thread


def _verify_collections():
    from core import nearby_records
    try:
        nearby_records._databases()
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        pass  # best effort: real requests verify again and report any problem to the person


def start():
    thread = Thread(target=_verify_collections, name='clovis-warmup', daemon=True)
    thread.start()
    return thread
