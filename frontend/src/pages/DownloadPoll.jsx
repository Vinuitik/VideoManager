import { useState, useRef } from 'react'

const POLL_INTERVAL_MS = 1000

export default function DownloadPoll() {
  const [url, setUrl] = useState('')
  const [job, setJob] = useState(null)   // null = no active download
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)       // useRef holds a value that doesn't trigger re-renders

  async function startDownload() {
    setError(null)
    const res = await fetch('/api/v1/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    const { job_id } = await res.json()

    // Start polling every POLL_INTERVAL_MS milliseconds
    intervalRef.current = setInterval(async () => {
      const r = await fetch(`/api/v1/jobs/${job_id}`)
      const data = await r.json()
      setJob(data)

      if (data.status === 'done' || data.status === 'error') {
        clearInterval(intervalRef.current)
        if (data.status === 'error') setError(data.error)
      }
    }, POLL_INTERVAL_MS)
  }

  const busy = job && job.status !== 'done' && job.status !== 'error'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold mb-1">Download — Polling</h1>
        <p className="text-sm text-zinc-400">
          Progress is fetched every {POLL_INTERVAL_MS}ms via GET /api/v1/jobs/:id
        </p>
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 bg-zinc-800 rounded px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="YouTube URL..."
          value={url}
          onChange={e => setUrl(e.target.value)}
          disabled={busy}
        />
        <button
          onClick={startDownload}
          disabled={busy || !url}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded text-sm font-medium"
        >
          Download
        </button>
      </div>

      {job && (
        <div className="space-y-2">
          <div className="h-2 bg-zinc-800 rounded overflow-hidden">
            {/* Tailwind inline styles via style= for dynamic values that can't be pre-computed */}
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${job.progress}%` }}
            />
          </div>
          <div className="flex justify-between text-sm text-zinc-400">
            <span>{job.status}</span>
            <span>{job.speed} — {job.eta}</span>
            <span>{job.progress.toFixed(1)}%</span>
          </div>
        </div>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  )
}
