from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os

from app.api.watch_queries import router as watch_queries_router
from app.api.scrapes import router as scrapes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    alembic_cfg = Config(
        os.path.join(os.path.dirname(__file__), "alembic.ini")
    )
    command.upgrade(alembic_cfg, "head")
    yield
    # Cleanup browser manager on shutdown
    from app.api.scrapes import _browser_manager

    if _browser_manager is not None:
        await _browser_manager.stop()


app = FastAPI(title="Price Scraper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(watch_queries_router)
app.include_router(scrapes_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
