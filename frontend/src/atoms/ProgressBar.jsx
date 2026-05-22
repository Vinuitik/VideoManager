// Atom: horizontal progress bar. value = 0-100, color = tailwind bg class.

export default function ProgressBar({ value = 0, color = 'bg-blue-500', error = false }) {
  return (
    <div className="h-1.5 bg-zinc-800 rounded overflow-hidden">
      <div
        className={`h-full transition-all duration-300 ${error ? 'bg-red-500' : color}`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
}
