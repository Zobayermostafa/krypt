import { useState } from 'react'
import DropZone from './DropZone'
import Spinner from './Spinner'
import DownloadLink from './DownloadLink'

interface EncryptResult {
  session_id: string
  key1: string
  key2: string
  key?: string
  files: { encrypted_image: string }
  message: string
}

export default function EncryptPanel() {
  const [image, setImage] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EncryptResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied1, setCopied1] = useState(false)
  const [copied2, setCopied2] = useState(false)
  const [copiedAll, setCopiedAll] = useState(false)

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

  const copyText = async (text: string, setCopiedState: (v: boolean) => void) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedState(true)
      setTimeout(() => setCopiedState(false), 2000)
    } catch {
      setError('Could not copy automatically. Select the key and copy it manually.')
    }
  }

  const downloadKeys = () => {
    if (!result) return
    const content = `Key 1 (Spatial Mask):\n${result.key1}\n\nKey 2 (Fourier Mask):\n${result.key2}\n`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'drpe-keys.txt'
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const reset = () => {
    setImage(null)
    setResult(null)
    setError(null)
    setCopied1(false)
    setCopied2(false)
    setCopiedAll(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Encrypt Photo</h2>
        <p className="text-sm text-gray-400">
          Upload any photo. DRPE generates an encrypted PNG and two separate keys that unlock it.
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

          <div className="rounded-xl bg-gray-950/60 border border-gray-800 p-6 space-y-5">
            <div>
              <h3 className="text-base font-semibold text-gray-200">Your Two Secret Keys</h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Both keys are required to decrypt. Key 1 unlocks the spatial phase; Key 2 unlocks the Fourier domain phase.
              </p>
            </div>

            {/* Key 1 */}
            <div className="space-y-2 p-3.5 bg-gray-900/60 border border-gray-800 rounded-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-indigo-400 inline-block"></span>
                  Key 1 (Spatial Mask)
                </span>
                <button
                  onClick={() => copyText(result.key1, setCopied1)}
                  className="text-xs text-gray-300 hover:text-white px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-md border border-gray-700 transition-all"
                >
                  {copied1 ? '✅ Copied' : '📋 Copy'}
                </button>
              </div>
              <code className="block w-full break-all select-all rounded-lg bg-gray-950 border border-gray-700/80 px-3 py-2 text-xs text-indigo-300 font-mono">
                {result.key1}
              </code>
            </div>

            {/* Key 2 */}
            <div className="space-y-2 p-3.5 bg-gray-900/60 border border-gray-800 rounded-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-purple-400 inline-block"></span>
                  Key 2 (Fourier Mask)
                </span>
                <button
                  onClick={() => copyText(result.key2, setCopied2)}
                  className="text-xs text-gray-300 hover:text-white px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-md border border-gray-700 transition-all"
                >
                  {copied2 ? '✅ Copied' : '📋 Copy'}
                </button>
              </div>
              <code className="block w-full break-all select-all rounded-lg bg-gray-950 border border-gray-700/80 px-3 py-2 text-xs text-purple-300 font-mono">
                {result.key2}
              </code>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <button
                onClick={() => copyText(`${result.key1}\n${result.key2}`, setCopiedAll)}
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 active:scale-95 text-white text-sm font-semibold rounded-xl border border-gray-700 transition-all"
              >
                {copiedAll ? '✅ Copied Both' : '📋 Copy Both Keys'}
              </button>
              <button
                onClick={downloadKeys}
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 active:scale-95 text-white text-sm font-semibold rounded-xl border border-gray-700 transition-all"
              >
                🔑 Save keys (.txt)
              </button>
            </div>

            <div className="rounded-lg bg-amber-950/30 border border-amber-700/40 p-3 text-xs text-amber-300/90">
              ⚠️ <strong>Save both keys now.</strong> They are not stored on the server. If either key is lost, the image cannot be recovered.
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
