import { useState } from 'react'
import DropZone from './DropZone'
import Spinner from './Spinner'
import DownloadLink from './DownloadLink'

interface EncryptResult {
  session_id: string
  key: string
  files: { encrypted_image: string }
  message: string
}

export default function EncryptPanel() {
  const [image, setImage] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EncryptResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleEncrypt = async () => {
    if (!image) return
    setLoading(true); setResult(null); setError(null)
    const form = new FormData()
    form.append('image', image)
    try {
      const res = await fetch('/api/encrypt', { method: 'POST', body: form })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || `Encryption failed (${res.status})`)
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setLoading(false) }
  }

  const copyKey = async () => {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result.key)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Could not copy automatically. Select the key and copy it manually.')
    }
  }

  const downloadKey = () => {
    if (!result) return
    const blob = new Blob([result.key + '\n'], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'drpe-key.txt'
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const reset = () => { setImage(null); setResult(null); setError(null); setCopied(false) }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Encrypt Photo</h2>
        <p className="text-sm text-gray-400">
          Upload any photo. DRPE generates an encrypted PNG and one secret key that unlocks it.
        </p>
      </div>

      {!result ? (
        <div className="space-y-6">
          <DropZone label="Select or Drop Photo" accept="image/*" hint="JPG, PNG, WEBP, BMP" value={image} onChange={setImage} />

          {error && (
            <div className="rounded-xl bg-red-950/40 border border-red-700/60 p-4 text-sm text-red-300">
              ⚠️ {error}
            </div>
          )}

          {loading ? (
            <Spinner label="Encrypting… this may take a moment for large images." />
          ) : (
            <button onClick={handleEncrypt} disabled={!image}
              className="w-full py-3.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              🔒 Encrypt Photo
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl bg-emerald-950/40 border border-emerald-700/60 p-5">
            <p className="text-base font-bold text-emerald-400">🎉 Encryption Complete!</p>
            <p className="text-xs text-emerald-300/80 mt-1">{result.message}</p>
          </div>

          <div className="rounded-xl bg-gray-950/60 border border-gray-800 p-6 space-y-4">
            <h3 className="text-sm font-semibold text-gray-200">Your secret key</h3>
            <code className="block w-full break-all select-all rounded-lg bg-gray-900 border border-gray-700 px-3 py-2.5 text-sm text-indigo-300 font-mono">
              {result.key}
            </code>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button onClick={copyKey}
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 active:scale-95 text-white text-sm font-semibold rounded-xl border border-gray-700 transition-all">
                {copied ? '✅ Copied' : '📋 Copy key'}
              </button>
              <button onClick={downloadKey}
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 active:scale-95 text-white text-sm font-semibold rounded-xl border border-gray-700 transition-all">
                🔑 Save key as file
              </button>
            </div>
            <div className="rounded-lg bg-amber-950/30 border border-amber-700/40 p-3 text-xs text-amber-300/90">
              ⚠️ <strong>Save this key now.</strong> It is not stored on the server, so if you lose it the image cannot be recovered. Anyone with the key can decrypt the image.
            </div>
          </div>

          <div className="rounded-xl bg-gray-950/60 border border-gray-800 p-6 space-y-4">
            <h3 className="text-sm font-semibold text-gray-200">Encrypted image</h3>
            <p className="text-xs text-gray-500">Available for about 10 minutes, so download it now.</p>
            <DownloadLink url={result.files.encrypted_image} filename="encrypted.png" label="Download Encrypted Image" icon="🖼️" />
          </div>

          {error && (
            <div className="rounded-xl bg-red-950/40 border border-red-700/60 p-4 text-sm text-red-300">
              ⚠️ {error}
            </div>
          )}

          <button onClick={reset} className="text-sm text-indigo-400 hover:text-indigo-300 font-medium">
            ← Encrypt another photo
          </button>
        </div>
      )}
    </div>
  )
}
