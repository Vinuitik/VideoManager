import { useEffect, useState } from 'react'
import { VideoCard } from '../molecules'

export default function Library() {
  const [videos, setVideos]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [playing, setPlaying] = useState(null)

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

      {playing && (
        <div className="bg-zinc-900 rounded overflow-hidden">
          <video
            key={playing}
            src={`/videos/${encodeURIComponent(playing)}`}
            controls
            autoPlay
            className="w-full max-h-[480px]"
          />
          <div className="flex justify-between items-center px-3 py-2 text-sm text-zinc-400">
            <span className="truncate">{playing}</span>
            <button onClick={() => setPlaying(null)} className="text-zinc-500 hover:text-zinc-300 ml-2">
              Close
            </button>
          </div>
        </div>
      )}

      <ul className="space-y-2">
        {videos.map(v => (
          <VideoCard
            key={v.name}
            name={v.name}
            size={v.size}
            isPlaying={playing === v.name}
            onPlay={() => setPlaying(playing === v.name ? null : v.name)}
            onDelete={() => deleteVideo(v.name)}
          />
        ))}
      </ul>
    </div>
  )
}
