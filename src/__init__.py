import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.auth.routes import auth_router
from src.config import config
from src.core.comments.routes import comment_router
from src.core.contributions.routes import contributions_router
from src.core.documents.routes import document_router
from src.core.proposals.routes import proposal_router
from src.core.versions.routes import version_router

from .exception_handler import (
    RequestValidationError,
    WriteWingedException,
    general_exception_handler,
    request_validation_handler,
    writewinged_exception_handler,
)
from .middleware import register_middleware

logger = logging.getLogger("writewinged.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("server started")
    yield
    logger.info("server stopped")


version = config.API_VERSION

app = FastAPI(
    version=version,
    title="Limarr-API",
    description="Collaborative writing",
    lifespan=lifespan,
)

# exception handlers
app.add_exception_handler(WriteWingedException, writewinged_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(Exception, general_exception_handler)

# middleware
register_middleware(app)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(document_router, prefix="/api/documents", tags=["documents"])
app.include_router(version_router, prefix="/api/documents", tags=["versions"])
app.include_router(
    contributions_router, prefix="/api/documents", tags=["contributions"]
)
app.include_router(proposal_router, prefix="/api/documents", tags=["proposals"])
app.include_router(comment_router, prefix="/api/documents", tags=["comments"])
