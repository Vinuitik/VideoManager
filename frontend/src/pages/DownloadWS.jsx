import { useState, useRef } from 'react'

// Each entry in the downloads map: { url, status, progress, speed, eta, filename }
// wsMap holds the actual WebSocket objects — kept in a ref so they don't trigger re-renders

export default function DownloadWS() {
  const [url, setUrl] = useState('')
  const [downloads, setDownloads] = useState({})  // { [jobId]: progressState }
  const wsMap = useRef(new Map())                  // { jobId -> WebSocket }

  function startDownload() {
    if (!url.trim()) return

    // Client generates the job ID — no server round-trip needed
    const jobId = crypto.randomUUID()
    const currentUrl = url
    setUrl('')

    // Register this download in state immediately so the row appears
    setDownloads(prev => ({
      ...prev,
      [jobId]: { url: currentUrl, status: 'connecting', progress: 0, speed: '', eta: '', filename: '' },
    }))

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v2/download`)
    wsMap.current.set(jobId, ws)

    ws.onopen = () => {
      ws.send(JSON.stringify({ url: currentUrl }))
      updateDownload(jobId, { status: 'downloading' })
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      if (msg.type === 'progress') {
        updateDownload(jobId, {
          status: 'downloading',
          progress: parseFloat(msg.progress) || 0,
          speed: msg.speed,
          eta: msg.eta,
        })
      } else if (msg.type === 'done') {
        updateDownload(jobId, { status: 'done', progress: 100, filename: msg.filename })
        wsMap.current.delete(jobId)
      } else if (msg.type === 'error') {
        updateDownload(jobId, { status: 'error', error: msg.message })
        wsMap.current.delete(jobId)
      }
    }

    ws.onerror = () => updateDownload(jobId, { status: 'error', error: 'WebSocket error' })
    ws.onclose  = () => {
      // If still downloading when closed, mark done (server closed after finishing)
      setDownloads(prev => {
        const d = prev[jobId]
        if (d && d.status === 'downloading') {
          return { ...prev, [jobId]: { ...d, status: 'done', progress: 100 } }
        }
        return prev
      })
    }
  }

  function updateDownload(jobId, patch) {
    // Functional update avoids stale closure issues when multiple downloads update simultaneously
    setDownloads(prev => ({
      ...prev,
      [jobId]: { ...prev[jobId], ...patch },
    }))
  }

  function dismissDownload(jobId) {
    wsMap.current.get(jobId)?.close()
    wsMap.current.delete(jobId)
    setDownloads(prev => {
      const next = { ...prev }
      delete next[jobId]
      return next
    })
  }

  const entries = Object.entries(downloads)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold mb-1">Download — WebSocket</h1>
        <p className="text-sm text-zinc-400">
          Real-time progress per chunk. Multiple downloads run simultaneously — each on its own WS connection.
        </p>
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 bg-zinc-800 rounded px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="YouTube URL..."
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && startDownload()}
        />
        <button
          onClick={startDownload}
          disabled={!url.trim()}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 rounded text-sm font-medium"
        >
          Download
        </button>
      </div>

      {entries.length === 0 && (
        <p className="text-zinc-500 text-sm">No active downloads.</p>
      )}

      <ul className="space-y-3">
        {entries.map(([jobId, d]) => (
          <li key={jobId} className="bg-zinc-900 rounded p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm truncate max-w-xs text-zinc-300">{d.url}</p>
              <button
                onClick={() => dismissDownload(jobId)}
                className="text-zinc-500 hover:text-zinc-300 text-xs ml-2 shrink-0"
              >
                ✕
              </button>
            </div>

            <div className="h-1.5 bg-zinc-800 rounded overflow-hidden">
              <div
                className={`h-full transition-all ${d.status === 'error' ? 'bg-red-500' : 'bg-emerald-500'}`}
                style={{ width: `${d.progress}%` }}
              />
            </div>

            <div className="flex justify-between text-xs text-zinc-400">
              <span className={d.status === 'error' ? 'text-red-400' : ''}>
                {d.status === 'error' ? d.error : d.status}
              </span>
              {d.status === 'downloading' && (
                <span>{d.speed} — {d.eta}</span>
              )}
              <span>{d.progress.toFixed(1)}%</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
