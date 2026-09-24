import { useEffect, useState } from 'react'
import EncryptPanel from './components/EncryptPanel'
import DecryptPanel from './components/DecryptPanel'
import VerifyPanel from './components/VerifyPanel'
import Icon from './components/Icon'

type Tab = 'encrypt' | 'decrypt' | 'verify'

const TABS: { id: Tab; label: string; description: string; icon: 'lock' | 'refresh' | 'verify' }[] = [
  { id: 'encrypt', label: 'Encrypt', description: 'Create a protected image', icon: 'lock' },
  { id: 'decrypt', label: 'Decrypt', description: 'Restore with your keys', icon: 'refresh' },
  { id: 'verify', label: 'Verify', description: 'Compare image integrity', icon: 'verify' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('encrypt')
  const [dark, setDark] = useState(() => localStorage.getItem('drpe-theme') !== 'light')

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    localStorage.setItem('drpe-theme', dark ? 'dark' : 'light')
  }, [dark])

  const active = TABS.find((tab) => tab.id === activeTab)!

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark"><Icon name="shield" size={21} /></div>
        <div className="brand-copy">
          <h1>DRPE Image Encryption</h1>
          <p>Double Random Phase Encoding <span className="brand-dot" /> Private by design</p>
        </div>
        <div className="header-actions">
          <span className="status-pill"><span className="status-dot" /> System ready</span>
          <button className="icon-button" onClick={() => setDark((value) => !value)} aria-label={`Switch to ${dark ? 'light' : 'dark'} mode`} title={`Switch to ${dark ? 'light' : 'dark'} mode`}>
            <Icon name={dark ? 'sun' : 'moon'} size={17} />
          </button>
        </div>
      </header>

      <main className="dashboard">
        <aside className="workflow-nav" aria-label="Workflow">
          <div className="eyebrow">WORKSPACE</div>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`workflow-item ${activeTab === tab.id ? 'is-active' : ''}`}
            >
              <span className="workflow-icon"><Icon name={tab.icon} size={17} /></span>
              <span><strong>{tab.label}</strong><small>{tab.description}</small></span>
            </button>
          ))}
          <div className="nav-note">
            <Icon name="info" size={16} />
            <p>Your files are processed locally by your connected DRPE server and removed after a short session.</p>
          </div>
        </aside>

        <section className="workspace">
          <div className="workspace-heading">
            <div><span className="eyebrow">{activeTab === 'verify' ? 'QUALITY CHECK' : 'IMAGE WORKFLOW'}</span><h2>{active.label}</h2></div>
            <span className="step-count">Step {activeTab === 'encrypt' ? '01' : activeTab === 'decrypt' ? '02' : '03'} <span>/ 03</span></span>
          </div>
          <div className="content-card">
          {activeTab === 'encrypt' && <EncryptPanel />}
          {activeTab === 'decrypt' && <DecryptPanel />}
          {activeTab === 'verify'  && <VerifyPanel />}
          </div>
        </section>
      </main>

      <footer className="footer"><span>DRPE Image Encryption</span><span>Secure image transformation for research and engineering</span>
      </footer>
    </div>
  )
}