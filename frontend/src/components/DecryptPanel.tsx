import { useState } from 'react'
import DropZone from './DropZone'
import Spinner from './Spinner'
import DownloadLink from './DownloadLink'

interface DecryptResult {
  session_id: string
  files: { decrypted_image: string }
  message: string
}

export default function DecryptPanel() {
  const [encryptedImage, setEncryptedImage] = useState<File | null>(null)
  const [key, setKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DecryptResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = !!(encryptedImage && key.trim())

  const handleDecrypt = async () => {
    if (!canSubmit) return
    setLoading(true); setResult(null); setError(null)
    const form = new FormData()
    form.append('encrypted_image', encryptedImage!)
    form.append('key', key.trim())
    try {
      const res = await fetch('/api/decrypt', { method: 'POST', body: form })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || `Decryption failed (${res.status})`)
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setLoading(false) }
  }

  const onKeyFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) setKey((await file.text()).trim())
    e.target.value = ''
  }

  const reset = () => {
    setEncryptedImage(null); setKey('')
    setResult(null); setError(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Decrypt Photo</h2>
        <p className="text-sm text-gray-400">
          Provide the encrypted PNG and the key you received when encrypting.
        </p>
      </div>

      {!result ? (
        <div className="space-y-6">
          <DropZone label="Encrypted Image (.png)" accept=".png,image/png" hint="The noise-like encrypted PNG" value={encryptedImage} onChange={setEncryptedImage} />

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label htmlFor="drpe-key" className="text-sm font-semibold text-gray-200">Key</label>
              <label className="text-xs text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer">
                Load from file
                <input type="file" accept=".txt,text/plain" className="hidden" onChange={onKeyFile} />
              </label>
            </div>
            <input
              id="drpe-key"
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="drpe1-…"
              spellCheck={false}
              autoComplete="off"
              className="w-full rounded-xl bg-gray-900/60 border border-gray-700 focus:border-indigo-500 focus:outline-none px-4 py-3 text-sm font-mono text-gray-100 placeholder-gray-600"
            />
          </div>

          {error && (
            <div className="rounded-xl bg-red-950/40 border border-red-700/60 p-4 text-sm text-red-300">
              ⚠️ {error}
            </div>
          )}

          {loading ? (
            <Spinner label="Decrypting… this may take a moment for large images." />
          ) : (
            <button onClick={handleDecrypt} disabled={!canSubmit}
              className="w-full py-3.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              🔓 Decrypt Photo
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl bg-emerald-950/40 border border-emerald-700/60 p-5">
            <p className="text-base font-bold text-emerald-400">✨ Decryption Complete</p>
            <p className="text-xs text-emerald-300/80 mt-1">{result.message}</p>
          </div>

          <div className="rounded-xl bg-gray-950/60 border border-gray-800 p-6 space-y-4">
            <h3 className="text-sm font-semibold text-gray-200">Reconstructed Image:</h3>
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <img src={result.files.decrypted_image} alt="Decrypted" className="max-h-60 rounded-xl border border-gray-800 shadow-md object-contain bg-black" />
              <DownloadLink url={result.files.decrypted_image} filename="decrypted.png" label="Download Decrypted Image" icon="🖼️" />
            </div>
          </div>

          <button onClick={reset} className="text-sm text-indigo-400 hover:text-indigo-300 font-medium">
            ← Decrypt another photo
          </button>
        </div>
      )}
    </div>
  )
}
