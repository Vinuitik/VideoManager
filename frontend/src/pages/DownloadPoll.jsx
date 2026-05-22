import { useState, useRef } from 'react'
import { DownloadInput } from '../molecules'
import { ProgressBar, Badge } from '../atoms'

const POLL_INTERVAL_MS = 1000

export default function DownloadPoll() {
  const [job, setJob]     = useState(null)
  const [error, setError] = useState(null)
  const intervalRef       = useRef(null)

  async function handleSubmit(url) {
    setError(null)
    setJob(null)

    const res = await fetch('/api/v1/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    const { job_id } = await res.json()

    intervalRef.current = setInterval(async () => {
      const r    = await fetch(`/api/v1/jobs/${job_id}`)
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
          Progress fetched every {POLL_INTERVAL_MS}ms via GET /api/v1/jobs/:id
        </p>
      </div>

      <DownloadInput onSubmit={handleSubmit} disabled={busy} accent="blue" buttonVariant="primary" />

      {job && (
        <div className="space-y-2">
          <ProgressBar value={job.progress} color="bg-blue-500" error={job.status === 'error'} />
          <div className="flex justify-between text-sm text-zinc-400">
            <Badge status={job.status} />
            <span>{job.speed} — {job.eta}</span>
            <span>{job.progress.toFixed(1)}%</span>
          </div>
        </div>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  )
}
