interface SpinnerProps {
  label?: string
}

export default function Spinner({ label = 'Processing…' }: SpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
      <span className="text-sm text-gray-300 font-medium">{label}</span>
    </div>
  )
}
