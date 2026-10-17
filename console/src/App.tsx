import { useEffect, useMemo, useState } from 'react'
import { AuditLog } from './AuditLog'
import { AuthError, createApi, type Api } from './api'
import { EscalationDetailView } from './EscalationDetailView'
import { EscalationList } from './EscalationList'
import { Login } from './Login'
import { usePolling } from './usePolling'

type Tab = 'pending' | 'decided' | 'audit'

const TOKEN_KEY = 'console.token'
const REVIEWER_KEY = 'console.reviewer'

export function App() {
  // The token lives in sessionStorage only: it disappears when the tab closes.
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY))
  const api = useMemo(() => (token ? createApi(token) : null), [token])

  function signOut() {
    sessionStorage.removeItem(TOKEN_KEY)
    setToken(null)
  }

  if (!api) {
    return (
      <Login
        onSignedIn={(t) => {
          sessionStorage.setItem(TOKEN_KEY, t)
          setToken(t)
        }}
      />
    )
  }
  return <Console api={api} onSignOut={signOut} />
}

interface ConsoleProps {
  api: Api
  onSignOut: () => void
  pollMs?: number | null
}

export function Console({ api, onSignOut, pollMs = 5000 }: ConsoleProps) {
  const [tab, setTab] = useState<Tab>('pending')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [reviewer, setReviewer] = useState(() => localStorage.getItem(REVIEWER_KEY) ?? '')

  useEffect(() => localStorage.setItem(REVIEWER_KEY, reviewer), [reviewer])

  const all = usePolling(() => api.list(), pollMs, 'all')
  const authFailed = all.error instanceof AuthError
  useEffect(() => {
    if (authFailed) onSignOut()
  }, [authFailed, onSignOut])

  const items = all.data ?? []
  const pending = items.filter((e) => e.status === 'pending')
  const decided = items.filter((e) => e.status !== 'pending').reverse()
  const visible = tab === 'pending' ? pending : decided

  function show(next: Tab) {
    setTab(next)
    setSelectedId(null)
  }

  return (
    <div className="shell">
      <header className="topbar">
        <h1>Escalation Console</h1>
        <label className="reviewer">
          Reviewer
          <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="your name" />
        </label>
        <button type="button" onClick={all.reload}>
          Refresh
        </button>
        <button type="button" onClick={onSignOut}>
          Sign out
        </button>
      </header>

      <nav className="tabs" aria-label="Views">
        <button type="button" aria-pressed={tab === 'pending'} onClick={() => show('pending')}>
          Pending ({pending.length})
        </button>
        <button type="button" aria-pressed={tab === 'decided'} onClick={() => show('decided')}>
          Decided ({decided.length})
        </button>
        <button type="button" aria-pressed={tab === 'audit'} onClick={() => show('audit')}>
          Audit log
        </button>
      </nav>

      {all.error && !authFailed && (
        <p role="alert" className="error">
          Could not refresh: {all.error.message}
        </p>
      )}

      {tab === 'audit' ? (
        <main className="single">
          <AuditLog api={api} />
        </main>
      ) : (
        <main className="split">
          <section aria-label="Queue">
            {all.loading && !all.data ? (
              <p className="empty">Loading…</p>
            ) : (
              <EscalationList
                items={visible}
                selectedId={selectedId}
                onSelect={setSelectedId}
                emptyText={tab === 'pending' ? 'Nothing is waiting for a human.' : 'No decisions yet.'}
              />
            )}
          </section>
          <section aria-label="Details">
            {selectedId ? (
              <EscalationDetailView
                key={selectedId}
                api={api}
                id={selectedId}
                reviewer={reviewer}
                onDecided={all.reload}
                onAuthError={onSignOut}
              />
            ) : (
              <p className="empty">Select an item to review it.</p>
            )}
          </section>
        </main>
      )}
    </div>
  )
}
