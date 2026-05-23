# Backend FLOWS

Files: main.py, config.py, state.py, routers/videos.py, routers/download_poll.py, routers/download_ws.py, routers/process.py, routers/credentials.py, services/downloader.py, services/processor.py, services/ollama_client.py, services/credentials_store.py, agent/loop.py, agent/prompts.py, mcp_tools/server.py, mcp_tools/tools/ytdlp.py, mcp_tools/tools/browser.py, mcp_tools/tools/cookies.py, mcp_tools/tools/rag.py, rag/client.py, rag/embedder.py, rag/seeder.py, rag/seed_cases.json

---

## Startup / Lifespan Flow

```
uvicorn starts → FastAPI app (main.py lifespan)
  → rag/seeder.seed_if_empty()
       → rag/client.get_collection()   singleton ChromaDB HttpClient
       → collection.count()
       → if > 0: return early (idempotent — safe to restart)
       → load rag/seed_cases.json  (15 cases, CoT chains, domain patterns)
       for each case:
         → rag/embedder.embed(problem + cot + solution_steps)
              POST http://ollama:11434/api/embeddings
              {model: "nomic-embed-text", prompt: text}
              → 768-dim float vector
         → collection.add(id="seed_{i}", document, embedding, metadata)
       → print "[RAG] Seeded 15 cases"
  → FastAPI serves routes

Failure modes:
  ChromaDB not ready → exception caught, printed, server still starts
  Ollama not ready   → embed() raises httpx error, caught, server still starts
  Re-seeding on restart → collection.count() > 0 → skipped, no duplicate entries
```

To change the seed data: `rag/seed_cases.json` — edit or add cases, then delete the ChromaDB volume and restart to force re-seed
To change the embed model: `config.EMBED_MODEL` env `EMBED_MODEL` (currently `nomic-embed-text`)
To change the agent LLM: `config.AGENT_MODEL` env `AGENT_MODEL` (currently `qwen2.5:3b`)

---

## Video CRUD Flow

```
GET /api/videos/
  → routers/videos.list_videos()
  → Path(VIDEOS_DIR).iterdir()
  → sorted by mtime descending
  → [{name, size, modified_at}]

DELETE /api/videos/{filename}
  → routers/videos.delete_video()
  → path.resolve().is_relative_to(videos_root)  ← path traversal guard
  → path.unlink()
```

To change the watched folder: `VIDEOS_DIR` env var → `config.VIDEOS_DIR`
To add metadata (duration, thumbnail): `routers/videos.list_videos()` — call `yt_dlp.YoutubeDL().extract_info(path, download=False)` per file (slow; cache results)

---

## Download Flow A — Polling (with Agent Escalation)

```
POST /api/v1/download {url}
  → routers/download_poll.start_download_poll()
  → state.new_job(url)   creates Job(status="queued") in state.jobs dict
  → BackgroundTasks.add_task(_run_download_with_agent, job)
       [FastAPI runs async background tasks directly in the event loop]
  → returns {job_id} immediately

_run_download_with_agent(job)  [async, runs in event loop]
  → asyncio.get_event_loop().run_in_executor(None, _ytdlp_sync)
       [yt-dlp is sync/blocking — run in threadpool to avoid blocking event loop]
       → services/downloader.download_sync(url, hook)
            → hook(d) fires per downloaded chunk:
                d["status"] == "downloading"  →  job.status/progress/speed/eta updated
                d["status"] == "finished"     →  job.status = "done", job.filename set
       → SUCCESS: job.status = "done"  ← normal path, agent never wakes
       → FAILURE: ytdlp_failed = True, job.error = str(exc)
  ↓ (only if ytdlp_failed)
  → agent/loop.AgentLoop(job).run()   ← see Agent ReAct Cycle below
       [still async in same event loop — concurrent with other downloads]

GET /api/v1/jobs/{job_id}
  → routers/download_poll.get_job()
  → plain dict read from state.jobs
  → {job_id, status, progress, speed, eta, filename, error, agent_log, agent_input_request}
  Note: agent_log grows in real time — poll frequently to stream agent reasoning to UI

POST /api/v1/jobs/{job_id}/input {value}
  → routers/download_poll.send_agent_input()
  → job.input_response = value
  → job._input_event.set()   wakes the agent loop if it's waiting for user input
  Use when: agent encounters CAPTCHA, MFA, or another interactive challenge
```

Why `run_in_executor` for yt-dlp: yt-dlp has no async API. Calling it directly in an async function blocks the event loop for minutes, preventing all other downloads/requests. The executor runs it in a separate thread while the event loop stays free.

Why the escalation is in download_poll only (not download_ws): WebSocket router owns its own threading model (`run_in_executor` → queue). Adding agent escalation there is a v2 task — the WS path stays yt-dlp only for now.

To change poll frequency on frontend: `src/pages/DownloadPoll.jsx → POLL_INTERVAL_MS`
To change max agent iterations: `agent/loop.MAX_ITERATIONS`
To skip agent and yt-dlp only: remove `if ytdlp_failed:` block in `_run_download_with_agent`

---

## Agent ReAct Cycle

```
agent/loop.AgentLoop(job).run()
  → job.status = "agent"
  → agent/prompts.load("system")
       → glob prompts/system_v*.md
       → picks highest version number (e.g. system_v2.md wins over system_v1.md)
       → reads file content
  → agent/prompts.render("think", url=url, domain=domain, error=job.error)
       → load("think") + .format(url=..., domain=..., error=...)
  → history = [{role:"system", content:system_prompt}, {role:"user", content:think_prompt}]

  for iteration in range(MAX_ITERATIONS=10):

    ── THINK ──
    → services/ollama_client.chat(history, tools=TOOL_DEFINITIONS)
         POST http://ollama:11434/api/chat
         {model:"qwen2.5:3b", messages:history, tools:[...], stream:false}
         timeout: 120s (long — qwen2.5:3b on 1650 GPU takes 5-30s per response)
         → returns message = {role:"assistant", content:"reasoning...", tool_calls:[...]}
    → AgentLoop._log("think", message.content)
         appends {role:"think", content:...} to job.agent_log
         clients see this via GET /api/v1/jobs/{id} → agent_log field

    ── ACT ──
    → services/ollama_client.parse_tool_calls(message)
         normalises tool_calls[].function.arguments
         (Ollama sometimes returns arguments as JSON string, sometimes as dict — handles both)
    → for each tool_call:
         → AgentLoop._log("act", "tool_name(args)")
         → AgentLoop._call_tool(name, args)
              → _TOOL_FN_MAP[name](**args)   direct Python call (no HTTP)
              Tools: query_rag, try_ytdlp, inspect_page_network,
                     authenticate_headless, write_case
         → AgentLoop._log("observe", str(result))

    ── OBSERVE ──
    → history.append({role:"assistant", content, tool_calls:[tc]})
    → history.append({role:"tool", name:tool_name, content:str(result)})
       [feeds observation back — Ollama sees it in next THINK]

    if tool_name == "try_ytdlp" and result.success:
      → job.status = "done", job.progress = 100.0, job.filename = result.filename
      → rag_tools.write_case(problem, solution, success=True, cot=built_cot)
      → return   ← done

    if no tool_calls in response: break   ← model decided to stop

  ↓ exhausted iterations or model stopped without success
  → job.status = "error"
  → rag_tools.write_case(..., success=False)   records failure for audit
```

Why direct function call instead of HTTP through /mcp: The FastMCP server at /mcp is for *external* callers (Claude Code, mobile). Internal calls from AgentLoop import `mcp_tools.tools.*` directly — same function, no network round-trip, no serialisation overhead.

Why history accumulates (not cleared between iterations): The LLM needs to see what it already tried to avoid repeating. History grows per iteration; if it gets too long for the context window, trim oldest tool result entries first (not implemented yet — 10 iterations on qwen2.5:3b is within 8k context).

To add a new tool to the agent:
1. Write `mcp_tools/tools/newtool.py` with an `async def` function
2. Add to `_TOOL_FN_MAP` in `agent/loop.py`
3. Add to `TOOL_DEFINITIONS` list in `agent/loop.py` (JSON schema)
4. Register in `mcp_tools/server.py` with `@mcp.tool()` (for external access)

To change what the agent says to Ollama: `prompts/system_v1.md` (or create `system_v2.md` — auto-picked)
To change the initial user message template: `prompts/think_v1.md`

---

## Prompt Versioning Flow

```
agent/prompts.load("system")
  → glob(PROMPTS_DIR + "/system_v*.md")
  → max(files, key=extract_version_number)
       e.g. [system_v1.md, system_v2.md] → picks system_v2.md
  → open and read file content

agent/prompts.render("think", url=url, domain=domain, error=error)
  → load("think") → file content with {url}, {domain}, {error} placeholders
  → .format(url=url, domain=domain, error=error)
```

PROMPTS_DIR: env var → `config.PROMPTS_DIR` (default `/prompts`)
Volume mount: `docker-compose.yml → backend.volumes → ./prompts:/prompts:ro`
Read-only mount ← prompts are never written by the container, only by the developer

To update a prompt without rebuilding: edit `prompts/system_v1.md` on host → change takes effect on next agent run (no restart, file read at runtime not at startup)
To version a prompt: create `prompts/system_v2.md` — the old v1 stays for rollback, v2 is picked automatically

---

## RAG Flow — Query

```
mcp_tools/tools/rag.query_rag(problem, n_results=3)
  → rag/embedder.embed(problem)
       POST http://ollama:11434/api/embeddings
       {model:"nomic-embed-text", prompt:problem}
       Why nomic-embed-text: best quality/size ratio for semantic similarity at 768 dims.
       Dedicated embedding model — NOT the agent LLM — means both can load simultaneously.
       → [float, float, ...] 768-dim vector
  → rag/client.get_collection()   singleton, created once
       chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
       collection "download_cases", distance metric: cosine
  → collection.query(query_embeddings=[vec], n_results=n, include=["documents","metadatas","distances"])
       ChromaDB computes 1 - cosine_similarity for each stored embedding
       returns top-n closest
  → returns [{document, similarity, tags, cot, solution_steps, requires_auth, requires_cookies}]
       similarity = 1.0 - distance  (1.0 = identical, 0.0 = unrelated)
       Caller (AgentLoop / Ollama) decides how to use the result

Why RAG before agent reasoning: the LLM (qwen2.5:3b) is a relatively small model with limited
world knowledge about obscure download patterns. Giving it a concrete prior solution from the
knowledge base dramatically improves first-attempt success rate.
```

To inspect what's in the RAG: query ChromaDB directly via `GET http://localhost:8001` (chromadb container exposed at 8001 on host) or add a debug endpoint
To clear and re-seed: `docker volume rm videomanager_chroma_data && docker compose up`

---

## RAG Flow — Write Case

```
mcp_tools/tools/rag.write_case(problem, solution, success, cot, tags=[])
  → doc_text = "Problem: {problem}\n\nChain of thought: {cot}\n\nSolution: {solution}\n\nOutcome: success|failure"
  → rag/embedder.embed(doc_text)   same embed path as query
  → rag/client.get_collection()
  → collection.add(id="case_{uuid8}", document=doc_text, embedding=vec, metadata={...})
       metadata includes: tags, cot, solution_steps (JSON), success flag

Called by AgentLoop automatically:
  - On download success → records what worked + the CoT that got there
  - On iteration exhaustion → records failure + what was tried (so next time RAG warns)
  - Always called via write_case tool when Ollama explicitly calls it mid-loop

Why store failures too: future queries on the same domain will retrieve the failure case
and know not to repeat those approaches — saving iterations.
```

---

## MCP Tools Flow — External vs Internal

```
                    mcp_tools/tools/*.py
                   (plain async functions)
                         │
              ┌──────────┴───────────┐
              │                      │
    Internal caller            External caller
    (AgentLoop)                (Claude Code, future mobile)
              │                      │
    direct Python import       FastMCP HTTP server
    agent/loop._TOOL_FN_MAP    mcp_tools/server.py
    → fn(**args) — no HTTP     @mcp.tool() wrappers
                               app.mount("/mcp", mcp.http_app())
                               Streamable HTTP at /mcp
                               ← MCP 2025 spec
                                      │
                               .claude/settings.json
                               mcpServers.videomanager
                               url: http://localhost:8000/mcp
                               ← backend port 8000 exposed in docker-compose
```

Tools exposed via MCP (all callable by Claude Code in this session):
- `try_ytdlp(url, extra_opts, cookies_path)` → {success, filename, error}
- `inspect_page_network(url, cookies_path)` → {candidates: [{url, method, headers}], count}
- `authenticate_headless(url, domain, username, password)` → {success, cookies_path, error}
- `extract_browser_cookies(domain, browser)` → {success, cookies, error}  [limited in Docker]
- `query_rag(problem, n_results)` → [{document, similarity, cot, solution_steps}]
- `write_case(problem, solution, success, cot, tags)` → {stored, id}

To add a tool accessible to Claude Code: implement in `mcp_tools/tools/`, wrap in `mcp_tools/server.py`, restart backend.

---

## MCP Tool — try_ytdlp

```
mcp_tools/tools/ytdlp.try_ytdlp(url, extra_opts=None, cookies_path="")
  → services/downloader.build_ydl_opts(None)   builds base opts, no progress hook
       (progress_hook=None → no "progress_hooks" key in opts — yt-dlp skips hook loop)
  → merge extra_opts if provided (format, http_headers, videopassword, etc.)
  → if cookies_path: opts["cookiefile"] = cookies_path
  → asyncio.run_in_executor(None, _run)    yt-dlp is sync
       yt_dlp.YoutubeDL(opts).extract_info(url, download=True)
       → result.success = True, result.filename = prepared_filename
       OR result.success = False, result.error = str(exc)
  → return {success, filename, error}

Why structured result instead of raising: the agent loop checks result.success to decide
the next tool call. An exception would break the loop; a structured result allows
the agent to read the error and try a different approach.
```

Common `extra_opts` patterns the agent passes:
- `{"format": "best"}` — fallback when complex format selectors fail
- `{"http_headers": {"User-Agent": "...", "Referer": "..."}}` — bypass basic bot detection
- `{"cookiefile": "/tmp/vm_cookies_abc.txt"}` — authenticated session
- `{"videopassword": "secret"}` — Vimeo password-protected
- `{"external_downloader": "ffmpeg"}` — last-resort raw stream pull

---

## MCP Tool — inspect_page_network

```
mcp_tools/tools/browser.inspect_page_network(url, cookies_path="")
  → async_playwright().chromium.launch(headless=True)
  → new_context(user_agent="Chrome/125...")   realistic UA avoids basic bot blocks
  → if cookies_path: context.add_cookies(_parse_netscape_cookies(cookies_path))
  → page.on("request", on_request)
       on_request(request):
         check request.url against _VIDEO_PATTERNS:
           [\.m3u8, \.mp4, \.webm, /manifest, /playlist,
            videodelivery\.net, akamaized\.net, fastly\.net,
            cloudfront\.net, cdn.*video, media.*cdn]
         match → append {url, method, resource_type, headers} to candidates
  → page.goto(url, wait_until="networkidle", timeout=30s)
       "networkidle" = no pending requests for 500ms — JS has had time to fire XHRs
  → page.wait_for_timeout(3000)   extra wait for lazy-loaded video requests
  → browser.close()
  → return {candidates, count}

Why Playwright instead of requests/BeautifulSoup: modern video sites require JavaScript
execution to generate stream URLs. The URL visible in the browser's network tab only
exists after JS runs — yt-dlp and static scrapers cannot see it.

Why capture request headers too: stream URLs often require the same Origin/Referer/Cookie
headers that the browser sent. The agent can pass them to try_ytdlp via extra_opts.

To add more video URL patterns: `mcp_tools/tools/browser._VIDEO_PATTERNS`
To increase wait time for slow pages: `page.wait_for_timeout(ms)` in inspect_page_network
```

---

## MCP Tool — authenticate_headless

```
mcp_tools/tools/browser.authenticate_headless(url, domain=None, username=None, password=None)

Credential resolution (if username/password not provided):
  → services/credentials_store.get(domain or urlparse(url).netloc)
       → SQLite SELECT credentials WHERE domain = ?
       → Fernet.decrypt(password_enc) → plaintext password
       → returns {username, password} or None
  → if None: return {success:False, error:"No credentials stored for domain"}

Headless login:
  → async_playwright().chromium.launch(headless=True)
  → page.goto(url, timeout=30s)
  → try selectors in order: input[type=email], input[name=email], input[name=username]...
       fill username into first matching selector
  → try selectors: input[type=password], #password, input[name=password]...
       fill password
  → page.keyboard.press("Enter")   submit form
  → wait_for_load_state("networkidle", timeout=15s)
  → context.cookies()
       → _write_netscape_cookies(tmp_path, cookies)
          writes Netscape HTTP Cookie File format (yt-dlp's --cookies format)
          tmp path: /tmp/vm_cookies_{random}.txt
  → return {success:True, cookies_path:tmp_path}

Why write Netscape format: yt-dlp's cookiefile option reads this exact format.
The agent passes cookies_path to try_ytdlp → opts["cookiefile"] = cookies_path.

Limitation: generic selector list works for most sites but fails on custom login flows
(JavaScript-rendered fields, multi-step auth). CAPTCHA/MFA causes timeout — agent
should set job.status="agent_waiting_input" and ask user (not yet implemented, v2).

To add site-specific login handling: subclass authenticate_headless or add domain
checks at the top of the function before the generic selector loop.
```

---

## Credentials Store Flow

```
POST /api/credentials {domain, username, password}
  → routers/credentials.upsert_credential()
  → services/credentials_store.upsert(domain, username, password)
       → _fernet.encrypt(password.encode())   AES-128 symmetric via Fernet
       → SQLite: INSERT OR REPLACE INTO credentials(domain, username, password_enc)
       DB path: CREDENTIALS_DB_PATH env → config.CREDENTIALS_DB_PATH (default /data/credentials.db)
       Key path: same dir, .key extension — generated once on first start, persisted in /data

GET /api/credentials
  → store.list_domains() → [domain, domain, ...]   passwords never returned

DELETE /api/credentials/{domain}
  → store.delete(domain) → True if found, 404 if not

Key persistence: if /data/credentials.key is deleted, all stored passwords become
unreadable (Fernet decryption will fail). The /data volume must be preserved.
```

To add credentials for YouTube: `POST /api/credentials {"domain":"accounts.google.com","username":"you@gmail.com","password":"..."}`
To back up credentials: copy both `/data/credentials.db` and `/data/credentials.key`
To rotate the encryption key: delete credentials.key, restart — all passwords must be re-entered

---

## Download Flow B — WebSocket (yt-dlp only, no agent)

```
WS /api/v2/download
  → routers/download_ws.ws_download()
  → websocket.accept()
  → websocket.receive_json() → {url}
  → asyncio.Queue() created
  → loop.run_in_executor(None, run)   yt-dlp in threadpool
       hook(d): loop.call_soon_threadsafe(queue.put_nowait, msg)
       None sentinel put when thread exits
  → async while: msg = await queue.get() → websocket.send_json(msg) → break on None
  → websocket.close()

Note: WS path does NOT escalate to agent (v1). If yt-dlp fails on WS,
the client receives a {"type":"error","message":"..."} and the WS closes.
Agent escalation for WS is planned for v2.
```

---

## FFmpeg Post-Process Flow

```
GET /api/process/presets
  → returns list(PRESETS.keys())   use to populate a dropdown in the UI

POST /api/process {filename, preset, overwrite}
  → routers/process.run_process()
  → path traversal guard
  → services/processor.PRESETS[preset]  →  af_filter string
  → asyncio.create_subprocess_exec("ffmpeg", "-i", input, "-af", filter, output, "-y")
  → await proc.communicate()
  → returns {filename}
```

To add a new FFmpeg preset: `services/processor.PRESETS` → add `"name": "ffmpeg_audio_filter_string"`

---

## Prometheus Metrics Flow

```
Prometheus container (every 15s)
  → GET backend:8000/metrics
  → prometheus-fastapi-instrumentator returns text/plain metrics
  → Prometheus stores as time series

Grafana → queries Prometheus via PromQL → renders panels
```

Metrics automatically tracked: `http_requests_total`, `http_request_duration_seconds`, request/response sizes.

---

## Request Routing (main.py)

| Prefix | Router | Purpose |
|---|---|---|
| /api/videos | routers/videos.py | CRUD — list, delete |
| /api/v1 | routers/download_poll.py | Download + poll + agent input |
| /api/v2 | routers/download_ws.py | Download via WebSocket |
| /api/process | routers/process.py | FFmpeg post-processing |
| /api/credentials | routers/credentials.py | Credentials vault CRUD |
| /api/health | main.py inline | Docker health check |
| /mcp | mcp_tools/server.py (FastMCP) | MCP Streamable HTTP — tools for Claude Code / mobile |
| /metrics | prometheus_fastapi_instrumentator | Prometheus scrape endpoint |

To add a new API resource: create `routers/myrouter.py`, add `app.include_router(...)` in `main.py`

---

## Debugging Guide

| Symptom | Where to look |
|---|---|
| Download never starts | `state.jobs[job_id].status` stuck at "queued" → check `_run_download_with_agent` exception in logs |
| Progress stuck at 0% | yt-dlp hook not firing → add `print(d)` in `hook()`, check format supports progress |
| Agent never starts | `ytdlp_failed` may be False — add print before `if ytdlp_failed:` in `download_poll._run_download_with_agent` |
| Agent loop stuck | Check `job.agent_log` via poll — which tool call is it waiting on? Playwright timeouts are 30s |
| Ollama not responding | `GET http://localhost:11434/` from host — is ollama container up? `docker logs videomanager-ollama-1` |
| qwen2.5:3b not found | Pull models: `docker exec videomanager-ollama-1 ollama pull qwen2.5:3b` |
| nomic-embed-text not found | `docker exec videomanager-ollama-1 ollama pull nomic-embed-text` |
| RAG returns no results | Check ChromaDB is seeded: if `seed_if_empty` logged an error at startup, seed failed |
| ChromaDB connection refused | `docker ps` — is chromadb container running? Check `CHROMA_HOST` / `CHROMA_PORT` env vars |
| Playwright crash in container | Missing system deps — Dockerfile runs `playwright install chromium --with-deps` but base image may need `apt-get install` of extra libs |
| authenticate_headless returns success=False "No credentials" | Store creds first: `POST /api/credentials {domain, username, password}` |
| Credentials decrypt error | `/data/credentials.key` was deleted or the volume was wiped — re-enter all passwords |
| WebSocket closes immediately | nginx `proxy_read_timeout` in `nginx/nginx.conf` |
| /mcp not responding | Backend must be running; port 8000 must be exposed (`docker-compose.yml backend.ports`) |
| FFmpeg produces no output | `run_process()` stderr returned in HTTP 500 body |

---

## Scaling Guide (for reference)

Current: in-memory `state.jobs` dict, single process, single Ollama container.

To scale downloads: replace `state.jobs` with Redis; replace `BackgroundTasks` with Celery/ARQ
To scale agent LLM: run multiple Ollama replicas behind a load balancer; increase `OLLAMA_NUM_PARALLEL`
To scale embeddings: `nomic-embed-text` is fast — embed calls rarely bottleneck; if they do, cache embedding results by text hash

---

## Test Suite

Files: tests/conftest.py, tests/test_unit.py, tests/test_videos.py, tests/test_download_poll.py, tests/test_process.py

Runner: `PYTHONPATH=backend pytest backend/tests/ -v`

New modules (agent, rag, mcp_tools) do not yet have dedicated test files — these are the gaps:

| Missing test file | What to test |
|---|---|
| tests/test_agent_loop.py | AgentLoop with mocked tool functions — verify think/act/observe sequencing, success path, exhaustion path |
| tests/test_mcp_tools.py | try_ytdlp with tmp fixture dir; inspect_page_network against a local HTTP server; query_rag against a pre-seeded test collection |
| tests/test_credentials.py | upsert/get/delete round-trip; decrypt-after-restart (reload fernet from disk key) |

To add a test for agent loop: patch `ollama_client.chat` with `AsyncMock`, patch tool functions — test that job.status transitions correctly.

---

## Change Index

| Thing to change | Where |
|---|---|
| Videos folder path | `VIDEOS_DIR` env → `config.VIDEOS_DIR` |
| Download format / quality | `services/downloader.build_ydl_opts()` → `format` key |
| yt-dlp output filename/path | `services/downloader.build_ydl_opts()` → `outtmpl` |
| Progress fields (poll) | `routers/download_poll._run_download_with_agent()` hook + `get_job()` |
| Progress fields (WebSocket) | `routers/download_ws.ws_download()` inner `hook()` |
| Agent max iterations | `agent/loop.MAX_ITERATIONS` |
| Agent LLM model | `config.AGENT_MODEL` (env `AGENT_MODEL`) |
| Agent system prompt | `prompts/system_v{N}.md` — create new version, auto-picked |
| Agent initial user message | `prompts/think_v{N}.md` — create new version |
| Agent tool list (add/remove) | `agent/loop.TOOL_DEFINITIONS` + `agent/loop._TOOL_FN_MAP` |
| Tools exposed via MCP | `mcp_tools/server.py` — add `@mcp.tool()` wrapper |
| Tool: video URL patterns | `mcp_tools/tools/browser._VIDEO_PATTERNS` |
| Tool: login field selectors | `mcp_tools/tools/browser.authenticate_headless()` selector lists |
| Embed model | `config.EMBED_MODEL` (env `EMBED_MODEL`) |
| RAG collection name | `config.CHROMA_COLLECTION` |
| RAG seed cases | `rag/seed_cases.json` — edit, then wipe chroma volume to re-seed |
| ChromaDB host/port | `CHROMA_HOST` / `CHROMA_PORT` env vars |
| Ollama host/port | `OLLAMA_URL` env → `config.OLLAMA_URL` |
| Ollama parallel slots | `OLLAMA_NUM_PARALLEL` env on ollama container (docker-compose) |
| Credentials DB path | `CREDENTIALS_DB_PATH` env → `config.CREDENTIALS_DB_PATH` |
| Credentials encryption key | `/data/credentials.key` (auto-generated; back up with the .db) |
| In-memory store → Redis | `state.py` → swap `jobs` dict for Redis client |
| FFmpeg presets | `services/processor.PRESETS` |
| API route prefixes | `main.py` → `app.include_router(..., prefix=...)` |
| Python version / OS packages | `backend/Dockerfile` |
| nginx WS timeout | `nginx/nginx.conf` → `proxy_read_timeout` |
| Prometheus scrape interval | `monitoring/prometheus.yml` → `scrape_interval` |
| Grafana dashboard panels | `monitoring/grafana/dashboards/videomanager.json` |
| Python dependencies | `backend/requirements.txt` |
| Prompts mount path | `docker-compose.yml` → `backend.volumes` + `PROMPTS_DIR` env |
