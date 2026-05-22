// Atom: coloured status label. Maps job status strings to colours.

const STATUS_STYLES = {
  queued:      'text-zinc-400',
  connecting:  'text-zinc-400',
  downloading: 'text-blue-400',
  done:        'text-emerald-400',
  error:       'text-red-400',
}

export default function Badge({ status }) {
  return (
    <span className={`text-xs font-medium ${STATUS_STYLES[status] ?? 'text-zinc-400'}`}>
      {status}
    </span>
  )
}
