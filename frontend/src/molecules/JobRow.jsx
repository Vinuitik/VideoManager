// Molecule: one download progress row — used by DownloadWS for the concurrent list.
import { ProgressBar, Badge, Button } from '../atoms'

export default function JobRow({ url, status, progress = 0, speed, eta, error, onDismiss }) {
  const isError = status === 'error'

  return (
    <li className="bg-zinc-900 rounded p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm truncate max-w-xs text-zinc-300">{url}</p>
        {onDismiss && (
          <Button variant="danger" onClick={onDismiss} className="px-2 py-0.5 text-xs ml-2 shrink-0">
            ✕
          </Button>
        )}
      </div>

      <ProgressBar value={progress} color="bg-emerald-500" error={isError} />

      <div className="flex justify-between text-xs text-zinc-400">
        <Badge status={status} />
        {status === 'downloading' && <span>{speed} — {eta}</span>}
        {isError && <span className="text-red-400">{error}</span>}
        <span>{progress.toFixed(1)}%</span>
      </div>
    </li>
  )
}
