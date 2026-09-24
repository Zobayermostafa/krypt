import { useCallback, useState, useRef } from 'react'

interface DropZoneProps {
  label: string
  accept?: string
  hint?: string
  value: File | null
  onChange: (file: File | null) => void
}

export default function DropZone({ label, accept, hint, value, onChange }: DropZoneProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (file: File | null) => {
      onChange(file)
    },
    [onChange]
  )

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files?.[0] ?? null
      handleFile(file)
    },
    [handleFile]
  )

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0] ?? null)
    e.target.value = ''
  }

  const isImage = value && value.type.startsWith('image/')
  const preview = isImage ? URL.createObjectURL(value) : null

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-semibold text-gray-200">{label}</span>
      <div
        className={`
          relative border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center
          cursor-pointer select-none transition-all duration-200 min-h-[160px]
          ${dragging
            ? 'border-indigo-500 bg-indigo-950/40 scale-[1.01]'
            : value
            ? 'border-emerald-500/80 bg-emerald-950/20'
            : 'border-gray-700 bg-gray-900/60 hover:border-indigo-500/60 hover:bg-gray-800/40'}
        `}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={onInputChange}
        />

        {value ? (
          <div className="flex flex-col items-center gap-3 w-full">
            {preview ? (
              <img
                src={preview}
                alt="preview"
                className="max-h-48 max-w-full rounded-lg object-contain shadow-md border border-gray-700/50"
              />
            ) : (
              <div className="w-14 h-14 rounded-full bg-indigo-950/60 border border-indigo-700/50 flex items-center justify-center text-2xl">
                📄
              </div>
            )}
            <div className="text-center">
              <span className="text-sm text-emerald-400 font-medium block truncate max-w-xs sm:max-w-md">
                {value.name}
              </span>
              <span className="text-xs text-gray-400 mt-0.5 block">
                {(value.size / 1024).toFixed(1)} KB &bull; Click or drop another to replace
              </span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center py-2">
            <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-2xl mb-1 text-gray-300">
              {dragging ? '📥' : '🖼️'}
            </div>
            <p className="text-sm font-medium text-gray-200">
              {dragging ? 'Drop the file here' : 'Drag & drop image or browse device'}
            </p>
            {hint && <p className="text-xs text-gray-400 max-w-xs">{hint}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
