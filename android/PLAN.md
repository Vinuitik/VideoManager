# VideoManager Android App — Plan

## What this app is
A native Android client for the VideoManager self-hosted backend. Personal use, sideloaded via USB/APK — no Play Store.

## Locked-in architecture decisions

| Decision | Choice | Why |
|---|---|---|
| Language | Java | user can read Java, not Kotlin |
| Server URL | `BuildConfig.SERVER_URL` in `build.gradle` | compile-time constant, no runtime settings screen, change = rebuild |
| Server detection | ping `/api/health` on startup (2s timeout) | clean mode switch, no user action needed |
| Local storage | MediaStore API | videos visible in Gallery + Files app, no permissions needed on Android 10+ |
| Local download | NewPipe Extractor library | Java-native YouTube extraction, no yt-dlp binary, no Python |
| Data layer | Repository pattern | `VideoRepository` interface → `ServerRepository` or `LocalRepository` — UI never knows which |
| UI | Material Design 3, minimal theming | looks clean, not loud; matches existing web app aesthetic |
| Modular boundaries | clean package separation | future merger with Notes app (see Phase 4) |

## Network
- Backend: FastAPI on laptop, exposed via Cloudflare Tunnel
- App uses user's own domain (set once in `build.gradle` before first build)
- HTTPS for HTTP calls, WSS for WebSocket — both handled transparently by Cloudflare

---

## Phases

### Phase 1 — Core app, server-connected ← START HERE

**Screens:**
- **Library** — list videos from server, tap to stream (ExoPlayer), delete
- **Download** — paste URL, WebSocket progress bar (sub-second updates)

**Tech:**
- Retrofit2 + OkHttp (HTTP + WebSocket)
- ExoPlayer (streams from server `/videos/` endpoint, range requests)
- `ServerRepository` implementation of `VideoRepository`
- `BuildConfig.SERVER_URL` wired through

**Done when:** app runs on phone over Cloudflare tunnel — can browse library, start a download with live progress, stream a video.

---

### Phase 2 — Local Mode (NewPipe fallback)

**Trigger:** health check on startup fails → app enters Local Mode automatically, shows a banner.

**Additions:**
- NewPipe Extractor dependency
- `LocalRepository` implementation of `VideoRepository`
- MediaStore write — downloaded videos appear in Gallery
- ExoPlayer reads from local MediaStore URI instead of server URL
- UI: "Offline — server unreachable" banner, Library shows phone videos only

**Scope limit:** no FFmpeg processing in Local Mode (server feature only). NewPipe covers YouTube + a handful of other sites — anything exotic still requires the server.

**Done when:** with server stopped, app downloads a YouTube video to phone storage and plays it back locally.

---

### Phase 3 — AI agent integration

**Backend side (Python):**
- LangGraph orchestrates AI workflows on the server
- New FastAPI endpoints: e.g. `POST /api/ai/summarise`, `POST /api/ai/extract-notes`
- API keys live server-side only — never in the APK

**Android side:**
- New screen or bottom sheet: AI actions on a selected video
- Calls backend AI endpoints via Retrofit (same pattern as Phase 1 — just more routes)
- No on-device LLM, no Spring AI (Spring AI is a Spring Boot server library, wrong layer for Android)
- Android is purely a UI client for the backend's AI

**Done when:** tap a video → request AI summary → result displayed on phone.

---

### Phase 4 — Merger with Notes app

**Context:** a separate Notes review app will exist. Goal is a unified super-app: video library + note review + AI extraction as the connective layer (AI pulls notes from videos, links to note cards).

**Architecture approach:**
- VideoManager becomes a self-contained module (video library, download, streaming)
- Notes becomes a self-contained module (note review, flashcard-style UI)
- Shared navigation shell + common UI components
- AI layer bridges both: extract notes from a video → create linked note cards

**When to start:** after Phase 2 is stable AND the Notes app exists as a separate project.

**Design constraint now:** keep package structure clean (`com.videomanager.library`, `com.videomanager.download`, etc.) so it can become a Gradle module without a rewrite.

---

## What NOT to do until explicitly planned

- No Kotlin
- No Play Store signing config or release keystore
- No FFmpeg on Android
- No on-device LLM / Ollama
- No Spring AI on Android
- No multi-user or auth (personal tool)
