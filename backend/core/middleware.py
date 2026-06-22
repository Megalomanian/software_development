from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class InferenceLoggingMiddleware(BaseHTTPMiddleware):
    """Logs inference request latency and errors for monitoring."""

    async def dispatch(self, request: Request, call_next):
        is_predict = request.url.path.startswith("/api/deployments/") and request.url.path.endswith(
            "/predict"
        )
        if not is_predict:
            return await call_next(request)

        start = time.time()
        error = None
        try:
            response: Response = await call_next(request)
        except Exception as e:
            error = str(e)
            response = Response(status_code=500, content=str(e))

        latency_ms = (time.time() - start) * 1000
        # Extract deployment_id from path: /api/deployments/{id}/predict
        parts = request.url.path.split("/")
        if len(parts) >= 5:
            deployment_id = parts[3]
            # Async log — fire and forget in production, use a queue
            try:
                from backend.core.dependencies import async_session
                from backend.services.monitoring_service import MonitoringService

                async with async_session() as db:
                    svc = MonitoringService(db)
                    body = None
                    if request.method == "POST":
                        try:
                            body = await request.body()
                            import json as _json
                            body = _json.loads(body)
                        except Exception:
                            pass
                    await svc.log_inference(
                        deployment_id=deployment_id,
                        request_data=body,
                        response_data=None,
                        latency_ms=latency_ms,
                        error=error,
                    )
            except Exception:
                pass  # don't block inference on logging failure

        return response
