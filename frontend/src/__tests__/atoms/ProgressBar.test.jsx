import { render } from '@testing-library/react'
import ProgressBar from '../../atoms/ProgressBar'

describe('ProgressBar', () => {
  it('sets width to the given value', () => {
    const { container } = render(<ProgressBar value={42} />)
    const bar = container.querySelector('.transition-all')
    expect(bar).toHaveStyle({ width: '42%' })
  })

  it('clamps value above 100 to 100%', () => {
    const { container } = render(<ProgressBar value={150} />)
    const bar = container.querySelector('.transition-all')
    expect(bar).toHaveStyle({ width: '100%' })
  })

  it('uses red colour on error', () => {
    const { container } = render(<ProgressBar value={50} error />)
    const bar = container.querySelector('.transition-all')
    expect(bar).toHaveClass('bg-red-500')
  })
})
