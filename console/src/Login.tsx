import { useState } from 'react'
import { AuthError, createApi } from './api'

interface Props {
  onSignedIn: (token: string) => void
}

export function Login({ onSignedIn }: Props) {
  const [token, setToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await createApi(token).list('pending') // the cheapest authenticated call
      onSignedIn(token)
    } catch (e) {
      setError(e instanceof AuthError ? 'That token was not accepted.' : `Could not reach the API: ${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login">
      <h1>Escalation Console</h1>
      <p>Held actions wait here for a human. This channel is separate from the tools the model can call.</p>
      <form onSubmit={submit}>
        <label htmlFor="token">Reviewer token</label>
        <input id="token" type="password" value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off" />
        <button type="submit" disabled={busy || token.length === 0}>
          Sign in
        </button>
        {error && <p role="alert" className="error">{error}</p>}
      </form>
    </main>
  )
}
