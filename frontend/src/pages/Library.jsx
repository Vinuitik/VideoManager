import { useEffect, useState } from 'react'

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`
}

export default function Library() {
  // useState: declare a reactive variable + its setter
  // When you call setVideos(...), React re-renders the component with the new value
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // useEffect: runs side-effects (data fetching, subscriptions) after render
  // The empty [] dependency array means "run once on mount" — like componentDidMount
  useEffect(() => {
    fetch('/api/videos/')
      .then(r => r.json())
      .then(data => { setVideos(data); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  async function deleteVideo(name) {
    await fetch(`/api/videos/${encodeURIComponent(name)}`, { method: 'DELETE' })
    // Remove deleted video from state without re-fetching
    setVideos(vs => vs.filter(v => v.name !== name))
  }

  if (loading) return <p className="text-zinc-400">Loading...</p>
  if (error)   return <p className="text-red-400">Error: {error}</p>
  if (!videos.length) return <p className="text-zinc-400">No videos yet. Download something!</p>

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Library</h1>
      <ul className="space-y-2">
        {videos.map(v => (
          // key= is required by React when rendering lists — helps it track which item changed
          <li key={v.name} className="flex items-center justify-between bg-zinc-900 rounded p-3">
            <div>
              <p className="font-medium">{v.name}</p>
              <p className="text-sm text-zinc-400">{formatBytes(v.size)}</p>
            </div>
            <button
              onClick={() => deleteVideo(v.name)}
              className="text-red-400 hover:text-red-300 text-sm"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
