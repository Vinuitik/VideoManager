// Molecule: URL input + submit button.
// Shared by DownloadPoll and DownloadWS — same UI, different onSubmit logic.
// Manages its own input state so the parent only sees the submitted URL.
import { useState } from 'react'
import { Input, Button } from '../atoms'

export default function DownloadInput({ onSubmit, disabled = false, accent = 'blue', buttonVariant = 'primary' }) {
  const [value, setValue] = useState('')

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setValue('')
  }

  return (
    <div className="flex gap-2">
      <Input
        accent={accent}
        placeholder="YouTube URL..."
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && submit()}
        disabled={disabled}
      />
      <Button
        variant={buttonVariant}
        onClick={submit}
        disabled={disabled || !value.trim()}
        className="shrink-0"
      >
        Download
      </Button>
    </div>
  )
}
