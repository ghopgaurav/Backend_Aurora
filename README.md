# Search API – Take-Home Assignment

A lightweight search service built on top of the provided `/messages` API.

The service:

- Periodically fetches all messages from the upstream `GET /messages` endpoint.
- Caches them in memory and serves search queries locally.
- Returns **ranked, paginated** results via a single `/api/v1/search` endpoint.
- Is deployed publicly on Fly.io and responds well under the **100 ms** requirement.

---

## 1. Live Service & API Overview

- **Live URL (health check):**  
  `https://search-api-sparkling-log-5301.fly.dev/` → `{"status": "running"}`

- **Interactive docs (OpenAPI/Swagger):**  
  `https://search-api-sparkling-log-5301.fly.dev/docs`

- **Search endpoint:**

  - **Method:** `POST`
  - **Path:** `/api/v1/search`
  - **Query parameters:**
    - `query` (string, required) – search query
    - `skip` (int, optional, default: `0`) – offset for pagination
    - `limit` (int, optional, default: sensible cap, e.g. `10` or `100`) – page size
  - **Response:** JSON with a list of matching messages and total match count  
    (message fields are derived from the upstream `/messages` schema, plus ranking info).

---

## 2. High-Level Design & Key Insights

### 2.1 Design Goals

The core goals were:

1. **Meet latency requirement:** endpoint responds in **< 100 ms**.
2. **Keep the system simple:** no external databases or search clusters.
3. **Be robust to upstream latency:** search performance should not depend on `GET /messages` at query time.
4. **Provide clear, explainable behaviour:** straightforward ranking and pagination.

### 2.2 Architecture Summary

**Data flow:**

1. **Startup:**
   - On application startup, the service calls the upstream `GET /messages` endpoint.
   - All messages (≈3.3k in the current dataset) are loaded into an in-memory cache.
   - A background task periodically refreshes this cache.

2. **Search request:**
   - User sends `POST /api/v1/search?query=...&skip=...&limit=...`.
   - The service operates **entirely on the in-memory cache**:
     - Filters messages by simple keyword matching.
     - Computes a lightweight relevance score.
     - Sorts results by score, then applies pagination (`skip`, `limit`).
   - Returns a JSON response to the client.

3. **Background refresh:**
   - A periodic async task calls `GET /messages` again.
   - On success, it replaces the in-memory cache with the new snapshot.

By decoupling search from the upstream API and moving all query-time work into memory, we keep the per-request latency very low and predictable.

---

## 3. Implementation Details

### 3.1 Technology Stack

- **Language:** Python 3.12
- **Framework:** FastAPI
- **HTTP client:** httpx (async)
- **Containerization:** Docker
- **Deployment:** Fly.io (region: `iad`, US-East)
- **Config & logging:**
  - Centralised settings module (`app/core/config.py`)
  - Centralised logger (`app/core/logging.py`)

### 3.2 Caching & Data Loading

- On startup, the app calls the upstream `GET /messages` endpoint with a large `limit` (e.g. 10,000) and stores all messages in an in-memory list.
- A background coroutine (`periodic_refresh_task`) triggers full cache refreshes at a configurable interval.
- Refresh behaviour:
  - On success: replace cache with the new dataset and log the count.
  - On failure (e.g. 4xx/5xx): log the error, but continue serving from the last known good cache.

**Rationale:**  
This design ensures:

- Search latency is **independent of upstream latency**.
- The service continues to function even if the upstream endpoint is temporarily unavailable.
- For the dataset size in this assignment, a full in-memory snapshot is both practical and fast.

### 3.3 Search & Ranking Strategy

The search implementation focuses on:

- **Simplicity**
- **Predictable performance**
- **Reasonable relevance** for keyword queries

High-level approach:

1. Normalize the query (e.g. lowercase, basic tokenisation).
2. For each cached message:
   - Check for keyword matches in message text and relevant metadata fields.
   - Compute a simple heuristic score (e.g. based on number/position of matches).
3. Keep only messages with score > 0.
4. Sort matches by descending score.
5. Apply pagination using `skip` and `limit`.

Given the dataset size (~3.3k messages), a linear scan over the in-memory list is sufficient and still keeps request-time latency very low.

### 3.4 Pagination

Pagination is done via:

- `skip`: number of results to skip from the top of the ranked list
- `limit`: maximum number of results to return

This makes it straightforward for the client to build “Next page/Previous page” behaviour without any cursor complexity.

---

## 4. Performance & Latency

### 4.1 Observed Behaviour

- **In-VM search latency:**  
  For a few thousand messages, search (filter + score + sort) completes in just a few milliseconds on a single shared CPU.

- **End-to-end latency (client → Fly.io → service → back):**
  - When tested from the US East region (close to Fly’s `iad` region), responses are **well under 100 ms**.
  - The majority of that time is network/TLS overhead rather than CPU work.

### 4.2 Why this meets the 100 ms requirement

The main design decisions that keep latency low:

1. **All queries are served from in-memory data**; no per-request calls to `GET /messages`.
2. **Simple scoring logic** with O(N) scan over a relatively small dataset.
3. **Single process with no cross-service network hops** inside the stack.

---

## 5. Bonus 1 – Alternative Approaches Considered

This section documents the design trade-offs that were considered before choosing the current architecture.

### 5.1 Approach A – Call `/messages` on every search request

- **Idea:** For each `/search` call, forward the query to `GET /messages`, then filter on the fly.
- **Pros:**
  - Very simple to implement.
  - Always works on the freshest data.
- **Cons:**
  - Latency tightly coupled to upstream response time.
  - Multiple network hops per request.
  - Risk of violating the **<100 ms** requirement under load or network variability.
- **Reason rejected:** Not robust enough for the latency target.

### 5.2 Approach B – Persist to a local database with full-text search

- **Idea:** On startup (or periodically), pull from `/messages` and index into a local DB (e.g. SQLite with FTS, or Postgres with full-text search).
- **Pros:**
  - More scalable if the dataset grows significantly.
  - Stronger query capabilities (phrases, weights, boolean logic).
- **Cons:**
  - More moving parts (database engine, migrations, connection management).
  - Additional operational complexity for a small assignment.
- **Reason not chosen:** Overkill for the dataset size and time constraints.

### 5.3 Approach C – Dedicated search engine (e.g. Elasticsearch, OpenSearch)

- **Idea:** Index messages into a dedicated search cluster, query it from the API.
- **Pros:**
  - Very powerful for large data and complex queries.
  - Built-in ranking, analyzers, filtering, aggregations, etc.
- **Cons:**
  - Requires provisioning and managing a search cluster.
  - Adds more operational surface area and cost.
- **Reason not chosen:** Unnecessary complexity for a lightweight, self-contained solution.

### 5.4 Chosen Approach – In-Memory Cache + Lightweight Ranking

- **Why this approach:**
  - Keeps the service **fast**, **simple**, and **self-contained**.
  - Meets the latency requirement comfortably.
  - Leaves room to evolve towards more advanced indexing if the dataset or query complexity grows.

---

## 6. Bonus 2 – How to Reduce Latency to ~30 ms

The assignment asks **how** we could reduce latency to ~30 ms. The following are realistic steps:

### 6.1 Infrastructure & Network Optimisations

1. **Region selection closer to users**  
   - Deploy the app in a region physically closest to the primary user base.
   - For example, if most users are in a specific US East metro, choose the nearest Fly.io region.

2. **Avoid cold starts**
   - Configure:
     - `min_machines_running = 1`
     - Disable or relax aggressive auto-stop settings
   - This keeps at least one warm instance alive, avoiding startup delays.

3. **Connection reuse & HTTP tuning**
   - Ensure the upstream `/messages` fetch uses HTTP/1.1 keep-alive or HTTP/2 (which httpx supports).
   - Although this does not affect per-query latency (since queries hit the cache), it reduces refresh overhead and avoids edge cases.

### 6.2 Application-Level Optimisations

1. **Pre-compute an in-memory inverted index**
   - On cache rebuild, build a mapping from token → list of message IDs.
   - At query time:
     - Tokenise the query.
     - Intersect/union posting lists instead of scanning all messages.
   - This would make search effectively **sub-linear** with respect to the total message count and push per-query CPU time to microseconds.

2. **Reduce payload size**
   - Return only the fields needed by the client for search results.
   - For non-critical metadata, provide a separate `/messages/{id}` fetch if needed.
   - Smaller responses mean less time spent serializing, compressing, and transmitting data.

3. **Optimise scoring logic**
   - Use fixed-width data structures and avoid unnecessary allocations inside the hot path.
   - Avoid per-request allocations that can be pre-computed at cache-build time.

With these changes, a realistic target is:

- **In-VM processing time:** sub-millisecond for typical queries.
- **End-to-end latency:** around **20–35 ms** for clients located close to the Fly.io region.

---

## 7. Running the Service Locally

### 7.1 Prerequisites

- Python 3.12
- `pip`  
- (Optional) Docker

### 7.2 Local (Python) Setup

```bash
git clone <your-repo-url>.git
cd search_api

python3.12 -m venv venv
source venv/bin/activate

### 7.3 Run with Docker

```bash
# Build image
docker build -t search-api .

# Run container
docker run -p 8000:8000 search-api

pip install --upgrade pip
pip install -r requirements.txt

# Run the app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
