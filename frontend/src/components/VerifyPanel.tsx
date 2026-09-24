import { useState } from 'react'
import DropZone from './DropZone'
import Spinner from './Spinner'
import DownloadLink from './DownloadLink'

interface VerifyResult {
  session_id: string
  verified: boolean
  stats: { mean_difference: number; max_difference: number; percent_changed: number }
  files: { difference_image: string }
  message: string
}

export default function VerifyPanel() {
  const [original, setOriginal] = useState<File | null>(null)
  const [decrypted, setDecrypted] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = !!(original && decrypted)

  const handleVerify = async () => {
    if (!canSubmit) return
    setLoading(true); setResult(null); setError(null)
    const form = new FormData()
    form.append('original', original!)
    form.append('decrypted', decrypted!)
    try {
      const res = await fetch('/api/verify', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Verification failed')
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setLoading(false) }
  }

  const reset = () => { setOriginal(null); setDecrypted(null); setResult(null); setError(null) }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Verify Photo Integrity</h2>
        <p className="text-sm text-gray-400">
          Compare the decrypted photo against the original using pixel-wise difference blending.
        </p>
      </div>

      {!result ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <DropZone label="Original Photo" accept="image/*" hint="The pre-encryption photo" value={original} onChange={setOriginal} />
            <DropZone label="Decrypted Photo" accept="image/*" hint="The decrypted photo to test" value={decrypted} onChange={setDecrypted} />
          </div>

          {error && (
            <div className="rounded-xl bg-red-950/40 border border-red-700/60 p-4 text-sm text-red-300">
              ⚠️ {error}
            </div>
          )}

          {loading ? (
            <Spinner label="Computing pixel-wise difference…" />
          ) : (
            <button onClick={handleVerify} disabled={!canSubmit}
              className="w-full py-3.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              ✅ Verify Photo Match
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Verdict */}
          <div className={`rounded-xl p-5 border flex items-start gap-4 ${
            result.verified
              ? 'bg-emerald-950/40 border-emerald-700/60'
              : 'bg-red-950/40 border-red-700/60'
          }`}>
            <span className="text-3xl">{result.verified ? '🛡️' : '❌'}</span>
            <div>
              <p className={`text-lg font-bold ${result.verified ? 'text-emerald-400' : 'text-red-400'}`}>
                {result.verified ? 'MATCH VERIFIED' : 'MISMATCH DETECTED'}
              </p>
              <p className="text-xs text-gray-300 mt-1">{result.message}</p>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Mean Diff" value={result.stats.mean_difference.toFixed(2)} hint="0 = identical"
              good={result.stats.mean_difference < 5} />
            <StatCard label="Max Diff" value={result.stats.max_difference.toFixed(0)} hint="Range 0–255"
              good={result.stats.max_difference < 15} />
            <StatCard label="Changed" value={`${result.stats.percent_changed.toFixed(1)}%`} hint="Noticeable pixels"
              good={result.stats.percent_changed < 1} />
          </div>

          {/* Diff Image */}
          <div className="rounded-xl bg-gray-950/60 border border-gray-800 p-6 space-y-4">
            <h3 className="text-sm font-semibold text-gray-200">
              Difference Map <span className="text-xs text-gray-500 font-normal">(black = match, bright = mismatch)</span>
            </h3>
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <img src={result.files.difference_image} alt="Difference" className="max-h-60 rounded-xl border border-gray-800 shadow-md object-contain bg-black" />
              <DownloadLink url={result.files.difference_image} filename="difference.png" label="Download Diff Map" icon="🖼️" />
            </div>
          </div>

          <button onClick={reset} className="text-sm text-indigo-400 hover:text-indigo-300 font-medium">
            ← Verify another pair
          </button>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, hint, good }: { label: string; value: string; hint: string; good: boolean }) {
  return (
    <div className="rounded-xl bg-gray-950/60 border border-gray-800 p-4 text-center">
      <p className={`text-2xl font-black ${good ? 'text-emerald-400' : 'text-red-400'}`}>{value}</p>
      <p className="text-xs font-semibold text-gray-200 mt-1">{label}</p>
      <p className="text-[11px] text-gray-500 mt-0.5">{hint}</p>
    </div>
  )
}