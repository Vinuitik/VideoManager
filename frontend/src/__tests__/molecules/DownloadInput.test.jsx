import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DownloadInput from '../../molecules/DownloadInput'

describe('DownloadInput', () => {
  it('calls onSubmit with the typed URL when Download is clicked', async () => {
    const onSubmit = vi.fn()
    render(<DownloadInput onSubmit={onSubmit} />)

    await userEvent.type(screen.getByPlaceholderText('YouTube URL...'), 'https://youtube.com/watch?v=123')
    await userEvent.click(screen.getByText('Download'))

    expect(onSubmit).toHaveBeenCalledWith('https://youtube.com/watch?v=123')
  })

  it('calls onSubmit when Enter is pressed', async () => {
    const onSubmit = vi.fn()
    render(<DownloadInput onSubmit={onSubmit} />)

    const input = screen.getByPlaceholderText('YouTube URL...')
    await userEvent.type(input, 'https://youtube.com/watch?v=abc{Enter}')

    expect(onSubmit).toHaveBeenCalledWith('https://youtube.com/watch?v=abc')
  })

  it('clears the input after submit', async () => {
    render(<DownloadInput onSubmit={vi.fn()} />)
    const input = screen.getByPlaceholderText('YouTube URL...')
    await userEvent.type(input, 'https://example.com')
    await userEvent.click(screen.getByText('Download'))
    expect(input).toHaveValue('')
  })

  it('does not call onSubmit when disabled', async () => {
    const onSubmit = vi.fn()
    render(<DownloadInput onSubmit={onSubmit} disabled />)
    await userEvent.click(screen.getByText('Download'))
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
