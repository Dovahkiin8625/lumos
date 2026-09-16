"""全局中间件。"""
from __future__ import annotations
import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from lumos.logging import get_logger, request_id_var
from lumos.errors import LumosError


log = get_logger("http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duration_ms = (time.perf_counter() - start) * 1000
        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=rid,
        )
        response.headers["X-Request-ID"] = rid
        return response


def register_middlewares(app):
    app.add_middleware(RequestIdMiddleware)