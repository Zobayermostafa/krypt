import { useCallback, useEffect, useState, useRef } from 'react'
import Icon from './Icon'

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
  const [preview, setPreview] = useState<string | null>(null)

  useEffect(() => {
    if (!isImage) { setPreview(null); return }
    const url = URL.createObjectURL(value)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [isImage, value])

  return (
    <div className="drop-field">
      <div className="field-label"><span>{label}</span><span className="field-type">{hint}</span></div>
      <div
        className={`drop-zone ${dragging ? 'is-dragging' : ''} ${value ? 'has-file' : ''}`}
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
          <div className="file-preview">
            {preview ? (
              <img
                src={preview}
                alt="Selected image preview"
                className="preview-image"
              />
            ) : (
              <div className="file-icon">
                <Icon name="file" size={22} />
              </div>
            )}
            <div className="file-copy">
              <strong title={value.name}>{value.name}</strong>
              <span>{(value.size / 1024).toFixed(1)} KB <span className="file-separator">·</span> Click to replace</span>
            </div>
            <button type="button" className="clear-file" onClick={(event) => { event.stopPropagation(); onChange(null) }} aria-label="Remove selected file" title="Remove selected file"><Icon name="x" size={15} /></button>
          </div>
        ) : (
          <div className="drop-prompt">
            <div className="upload-icon">
              <Icon name={dragging ? 'download' : 'upload'} size={20} />
            </div>
            <p>{dragging ? 'Drop the file here' : 'Drag and drop an image here'}</p>
            <span>or <b>browse your device</b></span>
          </div>
        )}
      </div>
    </div>
  )
}
