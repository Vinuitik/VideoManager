# Frontend FLOWS

Files: src/main.jsx, src/App.jsx, src/index.css, src/pages/Library.jsx, src/pages/DownloadPoll.jsx, src/pages/DownloadWS.jsx, vite.config.js, tailwind.config.js, postcss.config.js

---

## App Bootstrap

```
index.html  →  <div id="root">
  → src/main.jsx
      ReactDOM.createRoot(root).render(<BrowserRouter><App /></BrowserRouter>)
  → src/index.css   @tailwind base/components/utilities  (Tailwind injects all utility classes here at build time)
  → src/App.jsx     <Routes> renders the matching page component for the current URL
```

To add a new page:
1. Create `src/pages/MyPage.jsx`
2. Add `<Route path="/my-path" element={<MyPage />} />` in `App.jsx` inside `<Routes>`
3. Add `<NavLink to="/my-path">Label</NavLink>` in `App.jsx Nav()`
To debug blank page on load: check browser console for import errors — most common cause is a missing export in a page file

---

## Routing (App.jsx)

```
/            → Library.jsx        (video list + delete)
/poll        → DownloadPoll.jsx   (Version A — polling)
/websocket   → DownloadWS.jsx     (Version B — WebSocket)
```

React Router renders exactly one `<Route>` at a time based on the URL path.
`NavLink` auto-applies the active className when its `to=` matches the current URL — no manual tracking needed.

To add a nav link with an icon: wrap the label in an `<img>` or SVG inside the `NavLink` — Tailwind flex classes already handle alignment
To change active link style: `App.jsx Nav()` → the `active` string (currently `bg-zinc-700 text-white`)

---

## Library Page Flow (Library.jsx)

```
mount
  → useEffect([], fetch('/api/videos/'))
      on success: setVideos([...])  →  React re-renders with file list
      on error:   setError(msg)     →  error message shown

delete click
  → deleteVideo(name)
  → DELETE /api/videos/{name}
  → setVideos(vs => vs.filter(v => v.name !== name))
      removes item from local state — no re-fetch needed, UI updates instantly
```

React concept: `useState(x)` declares a reactive variable. Calling the setter triggers a re-render with the new value — equivalent to vanilla JS updating the DOM manually.
`useEffect(fn, [])` = "run fn once after first render" = vanilla `DOMContentLoaded`.

To add a refresh button: call `fetch('/api/videos/')` inside a handler, `setVideos(data)` — same as the mount effect
To add a sort/filter: transform the `videos` array before the `.map()` call, or add a second state variable for the filter value
To debug empty library: check `VIDEOS_DIR` env var in docker-compose matches the volume mount and the folder actually has files

---

## Download Poll Page Flow (DownloadPoll.jsx)

```
button click
  → POST /api/v1/download {url}
  → receives {job_id}
  → setInterval(POLL_INTERVAL_MS):
      GET /api/v1/jobs/{job_id}
      → setJob(data)   React re-renders progress bar with new %
      → if status === "done" or "error": clearInterval()
```

`useRef` holds the interval ID across renders without causing re-renders — if you stored it in `useState` it would trigger a re-render every time you saved it.
Vanilla equivalent: a module-level variable that persists across DOM updates.

To change poll frequency: `POLL_INTERVAL_MS` constant at top of file
To show multiple concurrent downloads: store `jobs` as an array/object in state, start a separate `setInterval` per job_id
To debug progress bar not moving: open Network tab in devtools, watch `/api/v1/jobs/{id}` responses — check `progress` field is changing

---

## Library — Video Player Flow (Library.jsx)

```
play button click
  → setPlaying(filename)
  → <video src="/videos/{encodeURIComponent(filename)}" controls autoPlay> renders
  → browser sends "Range: bytes=0-" to nginx
  → nginx slices file from disk, returns chunk with Content-Range header
  → browser plays; when user seeks: new Range request, nginx returns that slice

close button click / delete
  → setPlaying(null)   video element unmounts, playback stops
```

nginx serves `/videos/` as static files — range requests work automatically.
FastAPI is NOT involved in video playback at all.

To debug "video doesn't play": open DevTools → Network → filter `/videos/` — check nginx returns 206 Partial Content
To add a subtitle track: extend the `<video>` with a `<track>` element, serve `.vtt` files from `/videos/`
To add a seek-to-timestamp feature: use `videoRef.current.currentTime = seconds` on a `<video ref={videoRef}>`

---

## Download WebSocket Page Flow (DownloadWS.jsx)

```
button click
  → new WebSocket(ws://host/api/v2/download)
  → ws.onopen:
      ws.send(JSON.stringify({url}))   starts the download server-side
  → ws.onmessage(event):
      msg = JSON.parse(event.data)
      type === "progress"  →  setProgress({...})   bar updates sub-second, each chunk
      type === "done"      →  setProgress({status:"done", progress:100})
      type === "error"     →  setError(msg.message)
  → ws.onclose:   guard ensures status shows "done" if server closes before final message
```

**Multiplexing implemented.** Each `startDownload()` call opens its own WS and is tracked by a client-generated UUID in a `Map`. Multiple downloads render simultaneously.

`wsMap = useRef(new Map())` — holds live WebSocket objects, keyed by jobId. Not state (no re-renders when updated). `downloads` state holds only plain progress data — triggers re-renders.

`updateDownload` uses `setDownloads(prev => ...)` functional form — required when multiple downloads write simultaneously, otherwise they overwrite each other.

To debug WS not connecting: Network tab → WS → look for 101 Switching Protocols; if missing, check `nginx/nginx.conf` WS proxy headers
To add a download queue (sequential): hold a queue array in state, call `startDownload` inside `ws.onclose`
To cap concurrent downloads: check `wsMap.current.size` before opening a new socket

---

## Dev vs Prod

| Mode | How frontend reaches backend |
|------|------------------------------|
| `npm run dev` | Vite proxy: `/api` → `localhost:8000`, WebSocket upgraded too — `vite.config.js → server.proxy` |
| `docker compose up --build` | nginx proxies `/api/` (HTTP) and `/api/v2/download` (WS) — `nginx/nginx.conf` |

To change the dev proxy target (e.g. backend on different port): `vite.config.js` → `server.proxy['/api'].target`
To add HTTPS in prod: add SSL cert to nginx config — `nginx/nginx.conf`

---

## Tailwind Cheatsheet (for vanilla JS devs)

| Tailwind class | CSS equivalent |
|---|---|
| `flex gap-2` | `display:flex; gap:0.5rem` |
| `bg-zinc-900` | `background-color: #18181b` |
| `text-sm` | `font-size: 0.875rem` |
| `px-4 py-2` | `padding: 0.5rem 1rem` |
| `rounded` | `border-radius: 0.25rem` |
| `hover:bg-blue-500` | `:hover { background-color: #3b82f6 }` |
| `disabled:opacity-40` | `:disabled { opacity: 0.4 }` |
| `transition-all` | `transition: all 150ms` |
| `space-y-4` | `> * + * { margin-top: 1rem }` |
| `min-h-screen` | `min-height: 100vh` |

Dynamic values (e.g. progress %) cannot be Tailwind classes — use `style={{ width: \`${val}%\` }}` directly.
Tailwind removes unused classes at build time — only classes that appear literally in source files survive. Do not build class strings with string concatenation.

---

## Debugging Guide

| Symptom | Where to look |
|---------|--------------|
| Blank white page | Browser console → import error in a page file, likely missing export |
| Nav link not highlighting | `App.jsx Nav()` — check `to=` matches the `<Route path=` exactly |
| API calls fail in dev | `vite.config.js → server.proxy` — check target port matches backend |
| API calls fail in prod | `nginx/nginx.conf → location /api/` — check `proxy_pass` points to `backend:8000` |
| WS not connecting | Network tab → WS — check 101 response; if missing check `nginx/nginx.conf` WS headers |
| Progress bar jumpy (Poll) | Increase `POLL_INTERVAL_MS` or smooth with CSS `transition` |
| Tailwind classes not working | Check `tailwind.config.js → content` includes the file path |

---

## Change Index

| Thing to change              | Where                                              |
|------------------------------|----------------------------------------------------|
| Poll interval                | `src/pages/DownloadPoll.jsx` → `POLL_INTERVAL_MS`  |
| Progress bar colours         | `DownloadPoll.jsx` / `DownloadWS.jsx` → `bg-*` Tailwind classes |
| Nav links / pages            | `src/App.jsx` → `Nav()` + `<Routes>`               |
| Active nav link style        | `src/App.jsx Nav()` → `active` const string        |
| Tailwind theme / custom colours | `tailwind.config.js` → `theme.extend`           |
| Vite dev proxy target        | `vite.config.js` → `server.proxy`                 |
| Build output directory       | `vite.config.js` → `build.outDir` (default: dist) |
| Global CSS / fonts           | `src/index.css`                                    |
| WS concurrent download limit | `DownloadWS.jsx` → check `wsMap.current.size` in `startDownload()` |
| Video player max height      | `Library.jsx` → `<video className="max-h-[480px]">` |
