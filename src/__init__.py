from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.config import config
from src.auth.routes import auth_router
from .middleware import register_middleware


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

register_middleware(app)

app.include_router(auth_router, prefix=f"/api/auth", tags=["auth"])
