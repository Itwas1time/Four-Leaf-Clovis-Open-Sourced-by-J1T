"""One background download at a time; browser requests stay responsive."""
from threading import Lock, Thread
from uuid import uuid4
import time
from core.data_packs import PackStore

_lock = Lock()
_jobs = {}


def start(identifier):
    PackStore().definition(identifier)
    with _lock:
        if any(row["state"] == "working" for row in _jobs.values()):
            raise ValueError("A collection is already downloading. Its progress appears below.")
        for key in list(_jobs)[:-19]:
            if _jobs[key]["state"] != "working":
                del _jobs[key]
        key = uuid4().hex
        _jobs[key] = {"id": key, "pack": identifier, "state": "working", "phase": "Starting download",
                      "received": 0, "total": 0, "message": ""}

    def progress(phase, received, total):
        with _lock:
            _jobs[key].update(phase=phase, received=received, total=total)

    def run():
        try:
            PackStore().download(identifier, progress=progress)
            with _lock:
                _jobs[key].update(state="complete", phase="Installed",
                                  message="Collection installed and verified. Open its library to read the records.",
                                  finished=time.time_ns())
        except Exception as error:
            message = str(error) if isinstance(error, ValueError) else "Download interrupted. Retry to resume. Existing collections and dig records were preserved."
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
