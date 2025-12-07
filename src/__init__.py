from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db.main import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"server started...")
    await init_db()

    yield
    print(f"server stopped")


version = "v1"
app = FastAPI(
    version=version,
    title="Write-Winged",
    description="Collobarative writing--github for writers",
    lifespan=lifespan,
)
