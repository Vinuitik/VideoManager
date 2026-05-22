// Atom: the smallest interactive unit. No logic — just props → styled HTML.
// variant controls colour; all other HTML button props pass through via ...rest

const VARIANTS = {
  primary: 'bg-blue-600 hover:bg-blue-500 text-white',
  success: 'bg-emerald-600 hover:bg-emerald-500 text-white',
  danger:  'text-red-400 hover:text-red-300',
  ghost:   'bg-zinc-800 hover:bg-zinc-700 text-zinc-300',
}

export default function Button({ variant = 'primary', className = '', children, ...rest }) {
  return (
    <button
      className={`px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-40 ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
