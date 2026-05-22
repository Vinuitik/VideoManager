// Molecule: one row in the video library — filename, size, play toggle, delete.
import { Button } from '../atoms'

function formatBytes(bytes) {
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`
}

export default function VideoCard({ name, size, isPlaying, onPlay, onDelete }) {
  return (
    <li className="flex items-center justify-between bg-zinc-900 rounded p-3">
      <div className="min-w-0 mr-3">
        <p className="font-medium text-sm truncate">{name}</p>
        <p className="text-xs text-zinc-400">{formatBytes(size)}</p>
      </div>
      <div className="flex gap-2 shrink-0">
        <Button variant="ghost" onClick={onPlay}>
          {isPlaying ? 'Close' : 'Play'}
        </Button>
        <Button variant="danger" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </li>
  )
}
