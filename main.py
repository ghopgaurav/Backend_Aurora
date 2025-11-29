"""
FastAPI main application entry point.
"""

from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api import router
from app.services.cache_updater import full_refresh, periodic_refresh_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Load cache safely
    try:
        logger.info("[Startup] Loading all messages into cache...")
        await full_refresh()
    except Exception as e:
        logger.error(f"[Startup] Full refresh failed: {e}")
        logger.error("Continuing startup without cache...")

    # Background task
    task = asyncio.create_task(periodic_refresh_task())

    try:
        yield
    finally:
        logger.info("[Shutdown] Cleaning up…")
        try:
            task.cancel()
            await task
        except Exception:
            pass

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        workers=settings.WORKERS,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
