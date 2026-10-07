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


class BoundedRequestMiddleware:
    """Bound actual ASGI body bytes, including chunked requests without a length."""

    def __init__(self, app, max_bytes=MAX_REQUEST_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {}
        for name, value in scope.get("headers", []):
            name = name.lower()
            if name in headers and name in {b"host", b"origin", b"content-type", b"content-length"}:
                return await self._reject(send, 400, b"Ambiguous duplicate request headers.")
            headers[name] = value
        origin = headers.get(b"origin")
        if origin:
            host = headers.get(b"host", b"").decode("latin-1")
            expected_origin = scope.get("scheme", "http") + "://" + host
            if origin.decode("latin-1") != expected_origin:
                return await self._reject(send, 403, b"Cross-origin requests are disabled.")
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await self._reject(send, 400, b"Invalid Content-Length.")
        if declared < 0:
            return await self._reject(send, 400, b"Invalid Content-Length.")
        if declared > self.max_bytes:
            return await self._reject(send, 413, b"Request body too large.")
        messages = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                return await self._reject(send, 413, b"Request body too large.")
            messages.append(message)
            if len(messages) > 8192:
                return await self._reject(send, 413, b"Too many request chunks.")
            if not message.get("more_body", False):
                break
        if is_json_type(headers.get(b"content-type", b"").decode("latin-1")) and size:
            try:
                validate_json(b"".join(message.get("body", b"") for message in messages))
            except (ValueError, UnicodeError, RecursionError):
                return await self._reject(send, 400, b"Use valid JSON with finite numbers and Unicode text.")
        cursor = iter(messages)

        async def replay():
            return next(cursor, {"type": "http.disconnect"})

        async def with_headers(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                ]
            await send(message)

        await self.app(scope, replay, with_headers)

    @staticmethod
    async def _reject(send, status, body):
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        await send({"type": "http.response.body", "body": body})


def configure_local_api(app):
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    app.add_middleware(BoundedRequestMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(LOCAL_HOSTS))
