// Atom: styled text input. accent controls the focus ring colour.

const ACCENTS = {
  blue:    'focus:ring-blue-500',
  emerald: 'focus:ring-emerald-500',
}

export default function Input({ accent = 'blue', className = '', ...rest }) {
  return (
    <input
      className={`w-full bg-zinc-800 rounded px-3 py-2 text-sm outline-none focus:ring-2 ${ACCENTS[accent]} ${className}`}
      {...rest}
    />
  )
}
