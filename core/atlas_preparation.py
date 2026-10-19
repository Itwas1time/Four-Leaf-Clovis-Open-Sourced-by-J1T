"""Prepare the normal verified landing search while the browser loads assets."""
from threading import Event, Lock, Thread


class AtlasPreparation:
    def __init__(self,prepare=None):
        self._prepare=prepare
        self._lock=Lock()
        self._thread=None
        self.finished=Event()
        self.failed=False

    def start(self):
        with self._lock:
            if self._thread is not None:
                return False
            self._thread=Thread(target=self._run,name='clovis-atlas-preparation',daemon=True)
            try:
                self._thread.start()
            except RuntimeError:
                self.failed=True
                self.finished.set()
                return False
            return True

    def _run(self):
        try:
            if self._prepare is None:
                from core.atlas_catalog import search
                search()
            else:
                self._prepare()
        except Exception:
            # A warm-up result is never served directly. The ordinary search
            # still validates all collection signatures and reports failures.
            self.failed=True
        finally:
            self.finished.set()


def register_browser_preparation(server,preparation=None):
    from flask import request
    job=preparation if preparation is not None else AtlasPreparation()

    @server.before_request
    def prepare_browser_landing():
        # Health checks and API callers do not need a landing-page warm-up.
        # Browsers without Fetch Metadata retain the ordinary lazy search.
        if request.method=='GET' and request.path=='/' and request.headers.get('Sec-Fetch-Dest')=='document':
            job.start()

    return job
