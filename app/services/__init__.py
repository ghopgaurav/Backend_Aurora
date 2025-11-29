"""
Search service business logic.
"""

import logging
from typing import List, Tuple
from datetime import datetime
from app.core.config import settings
from app.core.cache import CACHE
from app.exceptions import SearchException
from app.schemas import MessageItem

logger = logging.getLogger(__name__)


# ============================================================
# Timestamp parser (for string timestamps in external API)
# ============================================================

def parse_timestamp(ts: str):
    """Convert an ISO timestamp string to a datetime object."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


# ============================================================
# Fuzzy matcher (Levenshtein distance)
# ============================================================

def edit_distance(a: str, b: str) -> int:
    """Efficient Levenshtein distance for short strings."""
    a = a or ""
    b = b or ""

    if abs(len(a) - len(b)) > 2:
        return 99  # treat as far → won't match

    dp = [[i + j for j in range(len(b) + 1)] for i in range(len(a) + 1)]

    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,        # deletion
                dp[i][j - 1] + 1,        # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )

    return dp[-1][-1]


# ============================================================
# Search Service
# ============================================================

class SearchService:
    """Service for handling search operations."""

    def __init__(self):
        self.timeout = settings.EXTERNAL_API_TIMEOUT
        self.api_url = settings.full_api_url

    # -----------------------------
    # Safe timestamp getter
    # -----------------------------
    def get_ts(self, item):
        ts = item.get("timestamp")

        # If timestamp is a string → parse it
        if isinstance(ts, str):
            ts = parse_timestamp(ts)
            if ts is None:
                return 0

        # If already datetime → convert to epoch
        if isinstance(ts, datetime):
            return ts.timestamp()

        return 0

    # -----------------------------
    # Main search function
    # -----------------------------
    async def search(self, query: str, skip: int = 0, limit: int = 10) -> Tuple[List[MessageItem], int]:
        if not query or not query.strip():
            raise SearchException("Search query cannot be empty")

        try:
            logger.info(f"Searching: query='{query}', skip={skip}, limit={limit}")

            all_messages = CACHE["messages"]
            total_messages = len(all_messages)
            logger.info(f"[DEBUG] Total messages in cache: {total_messages}")

            if not all_messages:
                logger.warning("[DEBUG] Cache is empty!")
                return [], 0

            query_lower = query.strip().lower()

            # ============================================================
            # Scoring function (ranking logic)
            # ============================================================

            def calculate_score(item):
                score = 0

                username = (item.get("user_name") or "").lower()
                message = (item.get("message") or "").lower()

                # EXACT MATCH (highest priority)
                if username == query_lower:
                    score += 5
                if message == query_lower:
                    score += 4

                # SUBSTRING MATCH
                if query_lower in username:
                    score += 3
                if query_lower in message:
                    score += 2

                # FUZZY MATCH (rare)
                # only apply fuzzy if both are short (<20 chars)
                if len(query_lower) < 20 and len(username) < 20:
                    dist_user = edit_distance(username, query_lower)
                    if dist_user == 1:
                        score += 2
                    elif dist_user == 2:
                        score += 1

                if len(query_lower) < 20 and len(message) < 20:
                    dist_msg = edit_distance(message, query_lower)
                    if dist_msg == 1:
                        score += 1

                # RECENCY TIE-BREAKER (ONLY if score > 0)
                if score > 0:
                    ts = item.get("timestamp")
                    if isinstance(ts, datetime):
                        score += ts.timestamp() / 1e12
                    elif isinstance(ts, str):
                        parsed = parse_timestamp(ts)
                        if parsed:
                            score += parsed.timestamp() / 1e12

                return score

            # ============================================================
            # Score all messages
            # ============================================================
            scored = []
            for item in all_messages:
                s = calculate_score(item)
                if s > 0:                # ⬅ FIX: irrelevant items filtered out
                    scored.append((s, item))

            logger.info(f"[DEBUG] {len(scored)} messages matched scoring > 0")

            # ============================================================
            # Sort by score DESC, timestamp DESC
            # ============================================================
            scored.sort(
                key=lambda x: (
                    x[0],                              # score
                    self.get_ts(x[1])                  # timestamp as tie-breaker
                ),
                reverse=True
            )

            ranked_items = [item for score, item in scored]

            # Pagination
            paginated = ranked_items[skip: skip + limit]

            # Convert dict to MessageItem
            results = [MessageItem(**item) for item in paginated]

            logger.info(
                f"[DEBUG] Returning {len(results)} results (ranked), total matches={len(scored)}"
            )

            return results, len(scored)

        # ----------------------------------------------------------
        # ERROR HANDLING
        # ----------------------------------------------------------
        except KeyError as e:
            logger.error(f"Cache error: {str(e)}")
            raise SearchException("Cache not initialized")

        except Exception as e:
            logger.error(f"Unexpected search error: {str(e)}")
            raise SearchException("Search failed")


search_service = SearchService()
