import { useState, useRef } from 'react'
import { DownloadInput } from '../molecules'
import { JobRow } from '../molecules'

export default function DownloadWS() {
  const [downloads, setDownloads] = useState({})
  const wsMap = useRef(new Map())

  function handleSubmit(url) {
    const jobId = crypto.randomUUID()

    setDownloads(prev => ({
      ...prev,
      [jobId]: { url, status: 'connecting', progress: 0, speed: '', eta: '', error: '' },
    }))

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v2/download`)
    wsMap.current.set(jobId, ws)

    ws.onopen = () => {
      ws.send(JSON.stringify({ url }))
      update(jobId, { status: 'downloading' })
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'progress') {
        update(jobId, { status: 'downloading', progress: parseFloat(msg.progress) || 0, speed: msg.speed, eta: msg.eta })
      } else if (msg.type === 'done') {
        update(jobId, { status: 'done', progress: 100 })
        wsMap.current.delete(jobId)
      } else if (msg.type === 'error') {
        update(jobId, { status: 'error', error: msg.message })
        wsMap.current.delete(jobId)
      }
    }

    ws.onerror = () => update(jobId, { status: 'error', error: 'WebSocket error' })
    ws.onclose = () => {
      setDownloads(prev => {
        const d = prev[jobId]
        if (d && d.status === 'downloading') return { ...prev, [jobId]: { ...d, status: 'done', progress: 100 } }
        return prev
      })
    }
  }

  function update(jobId, patch) {
    setDownloads(prev => ({ ...prev, [jobId]: { ...prev[jobId], ...patch } }))
  }

  function dismiss(jobId) {
    wsMap.current.get(jobId)?.close()
    wsMap.current.delete(jobId)
    setDownloads(prev => { const next = { ...prev }; delete next[jobId]; return next })
  }

  const entries = Object.entries(downloads)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold mb-1">Download — WebSocket</h1>
        <p className="text-sm text-zinc-400">
          Real-time progress. Multiple downloads run simultaneously.
        </p>
      </div>

      <DownloadInput onSubmit={handleSubmit} accent="emerald" buttonVariant="success" />

      {entries.length === 0 && <p className="text-zinc-500 text-sm">No active downloads.</p>}

      <ul className="space-y-3">
        {entries.map(([jobId, d]) => (
          <JobRow
            key={jobId}
            url={d.url}
            status={d.status}
            progress={d.progress}
            speed={d.speed}
            eta={d.eta}
            error={d.error}
            onDismiss={() => dismiss(jobId)}
          />
        ))}
      </ul>
    </div>
  )
}
