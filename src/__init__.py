from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.config import config
from src.auth.routes import auth_router
from .middleware import register_middleware
from .exception_handler import (
    writewinged_exception_handler,
    request_validation_handler,
    general_exception_handler,
    WriteWingedException,
    RequestValidationError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"server started...")
    await init_db()

    yield
    print(f"server stopped")


version = config.API_VERSION

app = FastAPI(
    version=version,
    title="Write-Winged",
    description="Collobarative writing",
    lifespan=lifespan,
)

# exception handlers
# todo: fix type error
app.add_exception_handler(WriteWingedException, writewinged_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(Exception, general_exception_handler)


register_middleware(app)

app.include_router(auth_router, prefix=f"/api/auth", tags=["auth"])
