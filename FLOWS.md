# VideoManager — FLOWS Index

Personal yt-dlp frontend. Paste URL → download with progress → stream from library.
Agent mode: URL fails yt-dlp → ReAct loop tries browser inspection, auth, RAG solutions.

## Subsystem FLOWS

| File | Covers |
|------|--------|
| [backend/FLOWS.md](backend/FLOWS.md) | FastAPI routes, yt-dlp download (poll + WS), agent ReAct loop, RAG (ChromaDB + Ollama embed), MCP tools, credentials store, Prometheus metrics |
| [frontend/FLOWS.md](frontend/FLOWS.md) | React pages, routing, Tailwind patterns, WS multiplexing, video player |
| [k6/README.md](k6/README.md) | Load test scenarios, how to run, how to read results |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | GitHub Actions CI — pytest + vitest + docker build |

---

## Overall Request Lifecycle

```
Browser → nginx :80
  ├── GET /           → serves React SPA (pre-compiled static files in nginx image)
  ├── GET /poll       → same SPA, React Router handles it client-side
  ├── GET /websocket  → same SPA
  │
  ├── GET /videos/*   → nginx serves video files DIRECTLY from disk (range requests)
  │                     backend is NOT involved in video playback
  │
  ├── /api/*          → proxied to FastAPI backend :8000 (HTTP)
  └── /api/v2/download → proxied with WS upgrade headers (WebSocket)

Claude Code / mobile clients → backend :8000 directly (port exposed in dev)
  └── /mcp            → FastMCP Streamable HTTP — agent tools (try_ytdlp, inspect_page_network, etc.)
```

## Container Map

| Container | Built from | Exposes | Purpose |
|---|---|---|---|
| `backend` | `backend/Dockerfile` | 8000 (public in dev) | FastAPI, yt-dlp, ffmpeg, agent loop, MCP server |
| `nginx` | `nginx/Dockerfile` (multi-stage) | 80 (public) | SPA + /videos streaming + API proxy |
| `ollama` | `ollama/ollama` (official) | 11434 (host) | LLM inference (qwen2.5:3b agent) + embeddings (nomic-embed-text) |
| `chromadb` | `chromadb/chroma` (official) | 8000 (internal) | Vector store for RAG download cases |
| `prometheus` | `prom/prometheus` (official) | 9090 | Scrapes `/metrics` from backend |
| `grafana` | `grafana/grafana` (official) | 3000 | Dashboards — open http://localhost:3000, no login |

Volumes:
- `C:\Users\ACER\Desktop\YT-Videos` → `/videos` in `backend` and `nginx`
- `./prompts` → `/prompts:ro` in `backend` (versioned prompt files, read-only)
- `videomanager_data` → `/data` in `backend` (SQLite credentials DB + key)
- `ollama_data` → `/root/.ollama` in `ollama` (downloaded model weights)
- `chroma_data` → `/chroma/chroma` in `chromadb` (embedded vector index)

**First-run model pull (once after `docker compose up`):**
```bash
docker exec videomanager-ollama-1 ollama pull nomic-embed-text
docker exec videomanager-ollama-1 ollama pull qwen2.5:3b
```
Then restart backend so the RAG seeder runs against a live ChromaDB and Ollama.

---

## Download Request Lifecycle — Agent Path

```
User pastes URL → POST /api/v1/download
  → yt-dlp attempt (threadpool)
      ├── SUCCESS → done, file in /videos, appears in Library
      └── FAILURE → agent/loop.AgentLoop(job).run()
            │
            ├─ query_rag → ChromaDB → known solution?
            │     ├── YES → apply solution → try_ytdlp → done
            │     └── NO  → continue loop
            │
            ├─ inspect_page_network → Playwright headless → intercept stream URLs
            │     └── try_ytdlp on intercepted URL
            │
            ├─ authenticate_headless → Playwright login → save cookies
            │     └── try_ytdlp with cookies
            │
            └─ write_case → ChromaDB ← records outcome (success or failure + full CoT)
                            next download from same domain benefits from this record

GET /api/v1/jobs/{id} → {status, progress, agent_log:[...], ...}
  status values: queued | downloading | agent | agent_waiting_input | done | error
  agent_log: [{role:"think"|"act"|"observe", content:"..."}] — streams reasoning in real time
```

---

## Common Tasks — Where to Go

### Add a new page or feature
→ [frontend/FLOWS.md](frontend/FLOWS.md) — "To add a new page" section

### Change video quality / format / subtitles
→ [backend/FLOWS.md](backend/FLOWS.md) — `services/downloader.build_ydl_opts()`

### Add a new agent tool
→ [backend/FLOWS.md](backend/FLOWS.md) — "To add a new tool to the agent" under Agent ReAct Cycle

### Change what the agent says to Ollama
→ Edit `prompts/system_v1.md` or create `prompts/system_v2.md` (auto-picked, no restart needed)

### Add known download solutions to RAG
→ Edit `rag/seed_cases.json`, wipe chroma volume, restart: `docker volume rm videomanager_chroma_data`

### Store credentials for a site (e.g. uni portal)
→ `POST /api/credentials {"domain":"uni.edu","username":"...","password":"..."}`
→ Agent will find them automatically when `authenticate_headless` is called for that domain

### Debug why the agent failed
→ Poll `GET /api/v1/jobs/{id}` → read `agent_log` array — each think/act/observe step is logged
→ [backend/FLOWS.md](backend/FLOWS.md) — Debugging Guide

### See live latency / error rates
→ http://localhost:3000 → VideoManager dashboard (Grafana)

### Run all tests locally
```bash
PYTHONPATH=backend pytest backend/tests/ -v
cd frontend && npm run test:run
```

### Run a load test
→ [k6/README.md](k6/README.md)

### Add a Grafana panel
→ http://localhost:3000 → VideoManager dashboard → Edit → Add panel
→ Dashboard JSON: `monitoring/grafana/dashboards/videomanager.json`

### Scale for multiple users
→ [backend/FLOWS.md](backend/FLOWS.md) — Scaling Guide

### Change the port nginx listens on
→ `docker-compose.yml` → `nginx.ports`

### Change the videos folder
→ `docker-compose.yml` → `backend.volumes` + `nginx.volumes` + `backend.environment.VIDEOS_DIR`
