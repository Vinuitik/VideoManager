import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import JobRow from '../../molecules/JobRow'

describe('JobRow', () => {
  const base = { url: 'https://youtube.com/watch?v=x', status: 'downloading', progress: 55, speed: '1.2MB/s', eta: '30s' }

  it('shows the URL', () => {
    render(<JobRow {...base} />)
    expect(screen.getByText(base.url)).toBeInTheDocument()
  })

  it('shows speed and eta while downloading', () => {
    render(<JobRow {...base} />)
    expect(screen.getByText('1.2MB/s — 30s')).toBeInTheDocument()
  })

  it('calls onDismiss when ✕ is clicked', async () => {
    const onDismiss = vi.fn()
    render(<JobRow {...base} onDismiss={onDismiss} />)
    await userEvent.click(screen.getByText('✕'))
    expect(onDismiss).toHaveBeenCalledTimes(1)
  })

  it('shows error text on error status', () => {
    render(<JobRow {...base} status="error" error="Network failed" />)
    expect(screen.getByText('Network failed')).toBeInTheDocument()
  })
})
