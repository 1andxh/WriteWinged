from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from .config import config
import logging

logger = logging.getLogger("uvicorn.access")


def register_middleware(app: FastAPI):
    allowed_hosts = [
        host.strip() for host in config.ALLOWED_HOSTS.split(",") if host.strip()
    ]

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )

    @app.middleware("http")
    async def get_request_info(request: Request, call_next):
        response = await call_next(request)
        if config.LOG_REQUESTS:
            client = request.client.host if request.client else "-"
            method = request.method
            path = request.url.path
            if request.url.query:
                path = f"{path}?{request.url.query}"
            http_version = request.scope.get("http_version", "1.1")
            status_code = response.status_code
            logger.info(
                '%s - "%s %s HTTP/%s" %d',
                client,
                method,
                path,
                http_version,
                status_code,
            )
        return response
