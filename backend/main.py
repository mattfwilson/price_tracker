import asyncio
import os
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.watch_queries import router as watch_queries_router
from app.api.scrapes import router as scrapes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup via thread executor to avoid event loop conflict
    # (alembic/env.py uses asyncio.run() internally, which requires no running loop)
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")

    # Start scheduler and register jobs from DB
    from app.services.scheduler import scheduler, register_jobs_from_db
    await register_jobs_from_db()
    scheduler.start()

    yield

    # Shutdown scheduler
    scheduler.shutdown(wait=False)

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

try:
    from app.api.alerts import router as alerts_router
    app.include_router(alerts_router)
except ImportError:
    pass


@app.get("/health")
async def health():
    return {"status": "ok"}
