import Icon from './Icon'

interface SpinnerProps {
  label?: string
}

export default function Spinner({ label = 'Processing…' }: SpinnerProps) {
  return (
    <div className="processing-state">
      <div className="spinner"><Icon name="spark" size={17} /></div>
      <div><strong>Processing image</strong><span>{label}</span></div>
    </div>
  )
}
