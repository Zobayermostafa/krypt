import { useState } from 'react'
import EncryptPanel from './components/EncryptPanel'
import DecryptPanel from './components/DecryptPanel'
import VerifyPanel from './components/VerifyPanel'

type Tab = 'encrypt' | 'decrypt' | 'verify'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'encrypt', label: 'Encrypt', icon: '🔒' },
  { id: 'decrypt', label: 'Decrypt', icon: '🔓' },
  { id: 'verify',  label: 'Verify',  icon: '✅' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('encrypt')

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <span className="text-3xl">🔐</span>
          <div>
            <h1 className="text-xl font-bold text-white">DRPE Image Encryption</h1>
            <p className="text-xs text-indigo-400">Double Random Phase Encoding</p>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-gray-800 bg-gray-900/50 px-6">
        <div className="max-w-4xl mx-auto flex gap-1 pt-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 text-sm font-semibold rounded-t-xl transition-all flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'bg-gray-950 text-indigo-400 border-x border-t border-gray-700'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Panel */}
      <main className="flex-1 px-6 py-8">
        <div className="max-w-4xl mx-auto bg-gray-900/40 border border-gray-800 rounded-2xl p-6 sm:p-8">
          {activeTab === 'encrypt' && <EncryptPanel />}
          {activeTab === 'decrypt' && <DecryptPanel />}
          {activeTab === 'verify'  && <VerifyPanel />}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-3 text-center text-xs text-gray-600">
        DRPE — Optical image encryption via Double Random Phase Encoding
      </footer>
    </div>
  )
}