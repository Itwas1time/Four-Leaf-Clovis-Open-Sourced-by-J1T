"""Shared request bounds for local research servers.

These controls protect the local tools from accidental exposure and oversized
requests. Internet hosting also needs authentication and infrastructure limits.
"""

import json
import math

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
MAX_REQUEST_BYTES = 2_000_000


def validate_json(body):
    """Reject nonfinite numbers and invalid Unicode before framework errors."""
    def reject_constant(_value):
        raise ValueError("JSON numbers must be finite")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("JSON numbers must be finite")
        return number

    data = json.loads(body, parse_constant=reject_constant, parse_float=finite_float)
    pending = [(data, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > 128:
            raise ValueError("JSON is too deeply nested")
        if isinstance(value, str):
            value.encode("utf-8")
        elif isinstance(value, dict):
            pending.extend((item, depth + 1) for pair in value.items() for item in pair)
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)


def is_json_type(content_type):
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or (media_type.startswith("application/") and media_type.endswith("+json"))


def configure_local_flask(server):
    from flask import abort, request

    server.config.update(MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES, TRUSTED_HOSTS=list(LOCAL_HOSTS))

    @server.before_request
    def local_origin_only():
        origin = request.headers.get("Origin")
        if origin and origin != request.host_url.rstrip("/"):
            abort(403, description="Cross-origin access to the local research server is disabled.")
        if is_json_type(request.content_type or ""):
            body = request.get_data(cache=True)
            if body:
                try:
                    validate_json(body)
                except (ValueError, UnicodeError, RecursionError):
                    abort(400, description="Use valid JSON with finite numbers and Unicode text.")

    @server.after_request
    def safe_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
