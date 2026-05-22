import { useEffect, useState } from 'react'

function formatBytes(bytes) {
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`
}

export default function Library() {
  const [videos, setVideos]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [playing, setPlaying] = useState(null)  // filename of the video currently open in the player

  useEffect(() => {
    fetch('/api/videos/')
      .then(r => r.json())
      .then(data => { setVideos(data); setLoading(false) })
      .catch(e  => { setError(e.message); setLoading(false) })
  }, [])

  async function deleteVideo(name) {
    await fetch(`/api/videos/${encodeURIComponent(name)}`, { method: 'DELETE' })
    setVideos(vs => vs.filter(v => v.name !== name))
    if (playing === name) setPlaying(null)
  }

  if (loading) return <p className="text-zinc-400">Loading...</p>
  if (error)   return <p className="text-red-400">Error: {error}</p>
  if (!videos.length) return <p className="text-zinc-400">No videos yet. Download something!</p>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Library</h1>

      {/* Inline video player — appears when a video is selected */}
      {playing && (
        <div className="bg-zinc-900 rounded overflow-hidden">
          {/*
            nginx serves /videos/ as static files with range request support.
            The browser sends "Range: bytes=X-Y" automatically when the user seeks —
            nginx slices the file and returns just that chunk. No backend involved.
          */}
          <video
            key={playing}              // key= forces React to remount when the video changes
            src={`/videos/${encodeURIComponent(playing)}`}
            controls
            autoPlay
            className="w-full max-h-[480px]"
          />
          <div className="flex justify-between items-center px-3 py-2 text-sm text-zinc-400">
            <span className="truncate">{playing}</span>
            <button onClick={() => setPlaying(null)} className="text-zinc-500 hover:text-zinc-300 ml-2 shrink-0">
              Close
            </button>
          </div>
        </div>
      )}

      <ul className="space-y-2">
        {videos.map(v => (
          <li key={v.name} className="flex items-center justify-between bg-zinc-900 rounded p-3">
            <div className="min-w-0 mr-3">
              <p className="font-medium text-sm truncate">{v.name}</p>
              <p className="text-xs text-zinc-400">{formatBytes(v.size)}</p>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => setPlaying(playing === v.name ? null : v.name)}
                className={`text-sm px-3 py-1 rounded ${
                  playing === v.name
                    ? 'bg-zinc-700 text-zinc-300'
                    : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
                }`}
              >
                {playing === v.name ? 'Close' : 'Play'}
              </button>
              <button
                onClick={() => deleteVideo(v.name)}
                className="text-red-400 hover:text-red-300 text-sm"
              >
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
