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
  const [key1, setKey1] = useState('')
  const [key2, setKey2] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DecryptResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = !!(encryptedImage && key1.trim() && key2.trim())

  const handleDecrypt = async () => {
    if (!canSubmit) return
    setLoading(true); setResult(null); setError(null)
    const form = new FormData()
    form.append('encrypted_image', encryptedImage!)
    form.append('key1', key1.trim())
    form.append('key2', key2.trim())
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
    if (!file) return
    const text = await file.text()
    // Auto-detect if file contains both keys or single key
    const m1Match = text.match(/drpe1-m1-[A-Za-z0-9_-]{47}/)
    const m2Match = text.match(/drpe1-m2-[A-Za-z0-9_-]{47}/)

    if (m1Match) setKey1(m1Match[0])
    if (m2Match) setKey2(m2Match[0])

    if (!m1Match && !m2Match) {
      // Fallback: split by lines
      const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
      if (lines[0]) setKey1(lines[0])
      if (lines[1]) setKey2(lines[1])
    }
    e.target.value = ''
  }

  // Key validation warnings
  const getKey1Warning = () => {
    const k = key1.trim()
    if (!k) return null
    if (k.startsWith('drpe1-m2-')) return '⚠️ This looks like Key 2 (Fourier mask)! Put it in the Key 2 field.'
    if (!k.startsWith('drpe1-m1-')) return '⚠️ Key 1 must start with drpe1-m1-'
    if (k.length !== 56) return `⚠️ Expected 56 chars, currently ${k.length}`
    return null
  }

  const getKey2Warning = () => {
    const k = key2.trim()
    if (!k) return null
    if (k.startsWith('drpe1-m1-')) return '⚠️ This looks like Key 1 (Spatial mask)! Put it in the Key 1 field.'
    if (!k.startsWith('drpe1-m2-')) return '⚠️ Key 2 must start with drpe1-m2-'
    if (k.length !== 56) return `⚠️ Expected 56 chars, currently ${k.length}`
    return null
  }

  const reset = () => {
    setEncryptedImage(null)
    setKey1('')
    setKey2('')
    setResult(null)
    setError(null)
  }

  const k1Warning = getKey1Warning()
  const k2Warning = getKey2Warning()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Decrypt Photo</h2>
        <p className="text-sm text-gray-400">
          Provide the encrypted PNG and both secret keys received when encrypting.
        </p>
      </div>

      {!result ? (
        <div className="space-y-6">
          <DropZone label="Encrypted Image (.png)" accept=".png,image/png" hint="The noise-like encrypted PNG" value={encryptedImage} onChange={setEncryptedImage} />

          {/* Key Inputs Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-200">Decryption Keys</span>
              <label className="text-xs text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer">
                📂 Load keys from file
                <input type="file" accept=".txt,text/plain" className="hidden" onChange={onKeyFile} />
              </label>
            </div>

            {/* Key 1 */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="drpe-key1" className="text-xs font-semibold text-indigo-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-400 inline-block"></span>
                Key 1 (Spatial Mask)
              </label>
              <input
                id="drpe-key1"
                type="text"
                value={key1}
                onChange={(e) => setKey1(e.target.value.trim())}
                placeholder="drpe1-m1-…"
                spellCheck={false}
                autoComplete="off"
                className={`w-full rounded-xl bg-gray-900/60 border ${
                  k1Warning ? 'border-amber-600/70 focus:border-amber-500' : 'border-gray-700 focus:border-indigo-500'
                } focus:outline-none px-4 py-2.5 text-xs font-mono text-gray-100 placeholder-gray-600`}
              />
              {k1Warning && <span className="text-[11px] text-amber-400">{k1Warning}</span>}
            </div>

            {/* Key 2 */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="drpe-key2" className="text-xs font-semibold text-purple-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-purple-400 inline-block"></span>
                Key 2 (Fourier Mask)
              </label>
              <input
                id="drpe-key2"
                type="text"
                value={key2}
                onChange={(e) => setKey2(e.target.value.trim())}
                placeholder="drpe1-m2-…"
                spellCheck={false}
                autoComplete="off"
                className={`w-full rounded-xl bg-gray-900/60 border ${
                  k2Warning ? 'border-amber-600/70 focus:border-amber-500' : 'border-gray-700 focus:border-purple-500'
                } focus:outline-none px-4 py-2.5 text-xs font-mono text-gray-100 placeholder-gray-600`}
              />
              {k2Warning && <span className="text-[11px] text-amber-400">{k2Warning}</span>}
            </div>
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
