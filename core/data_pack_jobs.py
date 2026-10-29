"""One collection transfer or installation at a time; requests stay responsive."""
from threading import Lock, Thread
from uuid import uuid4
import traceback
import time
from core.data_packs import PackStore

_lock = Lock()
_jobs = {}


def reserve(identifier, phase):
    definition = PackStore().definition(identifier)
    with _lock:
        if any(row["state"] == "working" for row in _jobs.values()):
            raise ValueError("A collection is already transferring or being checked. See Collection installation status.")
        for key in list(_jobs)[:-19]:
            if _jobs[key]["state"] != "working":
                del _jobs[key]
        key = uuid4().hex
        _jobs[key] = {"id": key, "pack": identifier, "state": "working", "phase": phase,
                      "title": definition['title'], "received": 0, "total": 0, "message": ""}
    return key


def update(key, **values):
    with _lock:
        _jobs[key].update(values)


def start(identifier):
    store = PackStore()
    definition = store.definition(identifier)
    if not definition['download_url']:
        raise ValueError('This collection uses a verified local ZIP. No online download is published in this catalog.')
    key = reserve(identifier, 'Starting download')

    def progress(phase, received, total):
        update(key, phase=phase, received=received, total=total)

    def run():
        try:
            store.download(identifier, progress=progress)
            with _lock:
                _jobs[key].update(state="complete", phase="Installed",
                                  message="Collection installed and verified. Open its library to read the records.",
                                  finished=time.time_ns())
        except Exception as error:
            # Keep the cause: it goes to the server log, and the person sees what kind of failure it was.
            traceback.print_exc()
            message = str(error) if isinstance(error, ValueError) else (
                f"Download stopped ({type(error).__name__}: {str(error)[:160]}). "
                "Retry to resume. Existing collections and dig records were preserved.")
            with _lock:
                _jobs[key].update(state="failed", phase="Download stopped", message=message,
                                  finished=time.time_ns())

    Thread(target=run, name="clovis-collection-download", daemon=True).start()
    return key


def status(key):
    if not isinstance(key, str) or len(key) != 32:
        return None
    with _lock:
        value = _jobs.get(key)
        return dict(value) if value else None
