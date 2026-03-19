from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    alembic_cfg = Config(
        os.path.join(os.path.dirname(__file__), "alembic.ini")
    )
    command.upgrade(alembic_cfg, "head")
    yield


app = FastAPI(title="Price Scraper", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
