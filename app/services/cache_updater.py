"""
Cache update logic — Full + Incremental refresh.
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.core.cache import CACHE
from app.core.config import settings
from app.core.logging import logger


async def fetch_all_messages() -> List[Dict[str, Any]]:
    """Fetch ALL messages using a high limit."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                settings.full_api_url,
                params={"skip": 0, "limit": settings.FETCH_LIMIT},
                timeout=settings.EXTERNAL_API_TIMEOUT
            )
            response.raise_for_status()
            return response.json().get("items", [])
    except Exception as e:
        logger.error(f"Failed to fetch all messages: {str(e)}")
        return []


async def fetch_new_messages() -> List[Dict[str, Any]]:
    """Fetch new messages AFTER the latest timestamp in cache."""
    if CACHE["latest_timestamp"] is None:
        return []

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                settings.full_api_url,
                params={
                    "skip": len(CACHE["messages"]),
                    "limit": 200  # small batch for new messages
                },
                timeout=settings.EXTERNAL_API_TIMEOUT
            )
            response.raise_for_status()
            return response.json().get("items", [])
    except Exception as e:
        logger.error(f"Failed to fetch new messages: {str(e)}")
        return []


async def full_refresh():
    """Complete reload of ALL messages."""
    logger.info("[Cache] Performing FULL REFRESH...")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                settings.full_api_url,
                params={"skip": 0, "limit": settings.FETCH_LIMIT},
                timeout=settings.EXTERNAL_API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

        items = data.get("items", [])
        
        if items:
            CACHE["messages"] = items
            CACHE["last_updated"] = datetime.utcnow()
            CACHE["total_messages"] = data.get("total", len(items))
            
            try:
                CACHE["latest_timestamp"] = max(
                    (item.get("timestamp") for item in items if item.get("timestamp")),
                    default=None
                )
            except (KeyError, TypeError):
                CACHE["latest_timestamp"] = None

            logger.info(f"[Cache] Full refresh loaded {len(items)} messages. Total available: {CACHE['total_messages']}")
        else:
            logger.warning("[Cache] Full refresh returned no messages.")
    except Exception as e:
        logger.error(f"Full refresh failed: {str(e)}")


async def incremental_refresh():
    """Incremental refresh — fetch only new messages."""
    # Stop if we've already loaded all available messages
    if len(CACHE["messages"]) >= CACHE.get("total_messages", 0):
        logger.debug(f"[Cache] All messages loaded ({len(CACHE['messages'])} / {CACHE.get('total_messages', 0)}). Skipping incremental refresh.")
        return

    new_items = await fetch_new_messages()

    if not new_items:
        logger.debug("[Cache] No new messages.")
        return

    CACHE["messages"].extend(new_items)
    try:
        new_timestamps = [item.get("timestamp") for item in new_items if item.get("timestamp")]
        if new_timestamps:
            CACHE["latest_timestamp"] = max(new_timestamps)
    except (KeyError, TypeError):
        pass

    logger.info(f"[Cache] Incremental refresh: +{len(new_items)} messages")


async def periodic_refresh_task():
    """Runs full + incremental refresh logic."""
    last_full_refresh = datetime.utcnow()

    while True:
        try:
            now = datetime.utcnow()

            # Full refresh every X hours
            if now - last_full_refresh > timedelta(hours=settings.FULL_REFRESH_HOURS):
                await full_refresh()
                last_full_refresh = now
            else:
                # Incremental update every N seconds
                await incremental_refresh()

            await asyncio.sleep(settings.INCREMENTAL_REFRESH_SECONDS)
        except asyncio.CancelledError:
            logger.info("[Cache] Refresh task cancelled.")
            break
        except Exception as e:
            logger.error(f"[Cache] Error in refresh task: {str(e)}")
            await asyncio.sleep(settings.INCREMENTAL_REFRESH_SECONDS)
