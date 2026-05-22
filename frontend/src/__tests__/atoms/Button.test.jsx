import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Button from '../../atoms/Button'

// vitest: describe() groups related tests. it() (or test()) is one test case.
// render() mounts the component into jsdom. screen.getBy* queries the DOM.

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const handler = vi.fn()   // vi.fn() = a spy function that records calls
    render(<Button onClick={handler}>Click</Button>)
    await userEvent.click(screen.getByText('Click'))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('does not call onClick when disabled', async () => {
    const handler = vi.fn()
    render(<Button disabled onClick={handler}>Click</Button>)
    await userEvent.click(screen.getByText('Click'))
    expect(handler).not.toHaveBeenCalled()
  })

  it('applies danger variant class', () => {
    render(<Button variant="danger">Delete</Button>)
    expect(screen.getByText('Delete')).toHaveClass('text-red-400')
  })
})
