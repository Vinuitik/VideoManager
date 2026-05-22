import { useState, useRef } from 'react'

export default function DownloadWS() {
  const [url, setUrl] = useState('')
  const [progress, setProgress] = useState(null)  // null = no active download
  const [error, setError] = useState(null)
  const wsRef = useRef(null)  // hold WebSocket instance across renders

  function startDownload() {
    setError(null)
    setProgress({ status: 'connecting', progress: 0, speed: '', eta: '' })

    // ws:// in dev (Vite proxy handles it); in prod nginx upgrades the connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v2/download`)
    wsRef.current = ws

    ws.onopen = () => {
      // Once connected, send the URL as JSON — server starts downloading immediately
      ws.send(JSON.stringify({ url }))
      setProgress(p => ({ ...p, status: 'downloading' }))
    }

    ws.onmessage = (event) => {
      // Each message is a JSON packet from the server's hook()
      const msg = JSON.parse(event.data)
      if (msg.type === 'progress') {
        setProgress({
          status: 'downloading',
          progress: parseFloat(msg.progress) || 0,
          speed: msg.speed,
          eta: msg.eta,
        })
      } else if (msg.type === 'done') {
        setProgress(p => ({ ...p, status: 'done', progress: 100 }))
      } else if (msg.type === 'error') {
        setError(msg.message)
        setProgress(null)
      }
    }

    ws.onerror = () => setError('WebSocket connection failed')
    ws.onclose = () => {
      // Ensure we show done state even if server closes before final message
      setProgress(p => p && p.status === 'downloading' ? { ...p, status: 'done', progress: 100 } : p)
    }
  }

  const busy = progress && progress.status !== 'done' && progress.status !== 'error'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold mb-1">Download — WebSocket</h1>
        <p className="text-sm text-zinc-400">
          Progress is pushed by the server in real time over a persistent WS connection
        </p>
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 bg-zinc-800 rounded px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="YouTube URL..."
          value={url}
          onChange={e => setUrl(e.target.value)}
          disabled={busy}
        />
        <button
          onClick={startDownload}
          disabled={busy || !url}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 rounded text-sm font-medium"
        >
          Download
        </button>
      </div>

      {progress && (
        <div className="space-y-2">
          <div className="h-2 bg-zinc-800 rounded overflow-hidden">
            <div
              className="h-full bg-emerald-500 transition-all"
              style={{ width: `${progress.progress}%` }}
            />
          </div>
          <div className="flex justify-between text-sm text-zinc-400">
            <span>{progress.status}</span>
            <span>{progress.speed} — {progress.eta}</span>
            <span>{progress.progress.toFixed(1)}%</span>
          </div>
        </div>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  )
}
