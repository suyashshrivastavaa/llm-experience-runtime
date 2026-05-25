from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import ingest, index, query
from app.core.config import settings

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    settings.indices_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="LLM Experience Runtime",
    description="Developer infrastructure for LLM-powered experiences.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/v1")
app.include_router(index.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
