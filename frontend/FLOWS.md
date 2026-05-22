# Frontend FLOWS

Files: src/main.jsx, src/App.jsx, src/index.css, src/pages/Library.jsx, src/pages/DownloadPoll.jsx, src/pages/DownloadWS.jsx, vite.config.js, tailwind.config.js

---

## App Bootstrap

```
index.html  →  <div id="root">
  → src/main.jsx  ReactDOM.createRoot().render(<BrowserRouter><App /></BrowserRouter>)
  → src/index.css  @tailwind base/components/utilities  (Tailwind injects all utility classes here)
  → src/App.jsx    <Routes> mounts the correct page component based on URL
```

To add a new page:
1. Create `src/pages/MyPage.jsx`
2. Add `<Route path="/my-path" element={<MyPage />} />` in `App.jsx`
3. Add a `<NavLink to="/my-path">` in `App.jsx Nav()`

---

## Routing (App.jsx)

```
/            → Library.jsx    (video list + delete)
/poll        → DownloadPoll.jsx  (Version A — polling)
/websocket   → DownloadWS.jsx   (Version B — WebSocket)
```

React Router renders exactly one page component at a time.
`NavLink` auto-applies active styling when its `to=` matches current URL.

---

## Library Page Flow (Library.jsx)

```
mount
  → useEffect([], fetch('/api/videos/'))
  → setVideos([...])  →  React re-renders with video list

delete button click
  → deleteVideo(name)
  → DELETE /api/videos/{name}
  → setVideos(vs => vs.filter(...))  — removes item from local state, no re-fetch needed
```

Key React concept: `useState` holds data; calling the setter re-renders the component.
`useEffect(fn, [])` = "run fn once after first render" = equivalent to vanilla `document.addEventListener('DOMContentLoaded', fn)`

---

## Download Poll Page Flow (DownloadPoll.jsx)

```
button click
  → POST /api/v1/download {url}
  → receives {job_id}
  → setInterval(POLL_INTERVAL_MS):
      GET /api/v1/jobs/{job_id}
      → setJob(data)  →  progress bar re-renders
      → if status === done/error: clearInterval()
```

`useRef` holds the interval ID across renders without causing re-renders itself.
Vanilla equivalent: a module-level variable that doesn't reset on DOM updates.
To change poll frequency: `POLL_INTERVAL_MS` constant at top of file

---

## Download WebSocket Page Flow (DownloadWS.jsx)

```
button click
  → new WebSocket(ws://host/api/v2/download)
  → ws.onopen: ws.send({url})
  → ws.onmessage: JSON.parse(event.data)
      type === "progress"  →  setProgress({...})  →  bar updates every chunk
      type === "done"      →  setProgress({status:"done", progress:100})
      type === "error"     →  setError(msg)
  → ws.onclose: guard — ensure status shows "done" if closed mid-download
```

`wsRef = useRef(null)` holds the WebSocket instance so `startDownload` can reference it
without stale closure issues. Same pattern as `intervalRef` in DownloadPoll.
To send multiple downloads on one connection: add `job_id` to the send payload and route `onmessage` by it

---

## Dev vs Prod

| Mode | How frontend reaches backend |
|------|------------------------------|
| Dev (`npm run dev`) | Vite proxy: `/api` → `localhost:8000`, `ws:` upgraded too — `vite.config.js` |
| Prod (Docker) | nginx: `/api/` proxied, `/api/v2/download` WS-upgraded — `nginx/nginx.conf` |

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

Dynamic values (e.g. progress %) must use `style={{ width: \`${val}%\` }}` — Tailwind classes are static.

---

## Change Index

| Thing to change              | Where                                              |
|------------------------------|----------------------------------------------------|
| Poll interval                | `pages/DownloadPoll.jsx` → `POLL_INTERVAL_MS`      |
| Progress bar colours         | `pages/DownloadPoll.jsx` / `DownloadWS.jsx` → Tailwind `bg-*` classes |
| Nav links / pages            | `App.jsx` → `Nav()` + `<Routes>`                  |
| Tailwind theme / colours     | `tailwind.config.js` → `theme.extend`              |
| Vite dev proxy target        | `vite.config.js` → `server.proxy`                 |
| Build output directory       | `vite.config.js` → `build.outDir` (default: dist) |
