# Search API – Take-Home Assignment

A lightweight, high-performance search service built on top of the provided `/messages` API.

## Useful Links

- **Live Deployment:**  
  https://search-api-sparkling-log-5301.fly.dev  

- **API Docs (Swagger):**  
  https://search-api-sparkling-log-5301.fly.dev/docs

- **Upstream Messages API:**  
  https://november7-730026606190.europe-west1.run.app/messages  


# Performance Summary

The search engine consistently completes **all compute work in under 10 ms**.  


### Latency Breakdown
- **Internal compute time:** 3–7 ms  
  (tokenization, filtering, scoring, sorting over ~3.3k cached messages)
- **Network + TLS routing (Fly.io):** 40–60 ms - Network and infra changes needed (Discussed below)
  (edge proxy, certificate handshake, VM hop)
- **Total observed latency:** 55–90 ms

### Key Points
- Compute layer itself is extremely fast (<10 ms).
- Remaining latency comes from unavoidable infrastructure overhead.
- With regional placement + TLS offload, latency could approach ~30 ms.


---

# 1. Service Overview

The API exposes a single search endpoint:

### `POST /api/v1/search?query=...&skip=...&limit=...`
- Performs in-memory search across all cached messages.
- Applies lightweight ranking and pagination.
- Returns results immediately with no upstream dependency during requests.

All data is periodically refreshed from the upstream `/messages` endpoint.


---

# 2. High-Level Design

### Goals
- Keep end-to-end latency <100 ms.
- Avoid dependency on upstream API during search.
- Deliver simple, predictable behaviour with clean ranking and pagination.

### Architecture
1. **Startup:**  
   Service fetches all messages (~3.3k) and stores them in an in-memory cache.
2. **Search requests:**  
   Query processed entirely from memory → filter → score → rank → paginate.
3. **Background refresh:**  
   Periodically re-fetches all messages and updates the cache.


---

# 3. Implementation Details

### Stack
- Python 3.12  
- FastAPI  
- httpx (async client)  
- Docker  
- Fly.io (region: `iad`)

### Caching
- Full dataset loaded at startup with a large `limit` (e.g., 10k).
- Async background task refreshes regularly.
- Failures do not interrupt service; last good cache stays active.

### Search Logic
- Lowercased keyword matching in `message` and `username`.
- Simple scoring based on keyword frequency.
- Sort by score, then apply `skip` + `limit`.

### Why It’s Fast
- Entire dataset fits comfortably in memory.
- Linear scan over ~3k objects is extremely cheap (<10 ms).
- No DB, no external services, no per-request network calls.


---

# 4. Alternative Approaches Considered

### A) Query upstream `/messages` each time  
Too slow and unreliable under network variance.

### B) Use SQLite / Postgres FTS  
Overkill for the dataset size; introduces unnecessary overhead.

### C) Use Elasticsearch / OpenSearch  
Powerful but adds large operational complexity.

### D) Final Choice — In-Memory Cache + Lightweight Ranking  
Simplest, fastest, and most reliable for the constraints of this assignment.


---

# 5. Path to ~30 ms Latency

To reduce global latency toward ~30 ms:

### Infrastructure
- Deploy closer to users (region locality).
- Reduce TLS handshake cost via keep-alive or terminating TLS earlier.
- Keep `min_machines_running = 1` to avoid cold starts.

### Application
- Pre-compute an inverted index for sub-millisecond lookups.
- Reduce payload size and avoid unnecessary fields.
- Micro-optimise scoring and tokenization during cache build.

The compute layer is already <10 ms, so remaining wins are infra-level.


---

# 6. Running Locally

## 6.1 Python Environment

```bash
git clone <your-repo>.git
cd search_api

python3.12 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
