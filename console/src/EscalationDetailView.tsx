import { useState } from 'react'
import type { Api } from './api'
import { RuleBadge, SourceBadge, StatusBadge } from './Badges'
import { describeAction } from './format'
import { ReviewPanel } from './ReviewPanel'
import { usePolling } from './usePolling'

interface Props {
  api: Api
  id: string
  reviewer: string
  onDecided: () => void
  onAuthError: (e: Error) => void
}

export function EscalationDetailView({ api, id, reviewer, onDecided, onAuthError }: Props) {
  const { data, error, reload } = usePolling(() => api.get(id), null, id)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  async function decide(action: () => Promise<{ result?: { executed: boolean; message?: string } }>) {
    setBusy(true)
    setMessage(null)
    try {
      const outcome = await action()
      const executed = outcome.result
      setMessage({
        kind: 'ok',
        text: executed ? (executed.executed ? 'Approved and executed.' : `Approved, but not executed: ${executed.message ?? 'see log'}`) : 'Rejected.',
      })
      reload()
      onDecided()
    } catch (e) {
      if ((e as { status?: number }).status === 401) onAuthError(e as Error)
      setMessage({ kind: 'error', text: (e as Error).message })
      reload()
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) return <p role="alert" className="error">Could not load {id}: {error.message}</p>
  if (!data) return <p className="empty">Loading…</p>

  return (
    <article className="detail" aria-label={`Escalation ${data.id}`}>
      <header>
        <h2>{describeAction(data)}</h2>
        <div className="card-badges">
          <StatusBadge status={data.status} />
          <RuleBadge rule={data.rule} />
          <SourceBadge source={data.source} />
        </div>
      </header>

      <dl className="facts">
        <dt>Why it was held</dt>
        <dd>{data.reason}</dd>
        <dt>What the user asked</dt>
        <dd>{data.user_request ?? <em>Not available: the server holding this action never sees the user's messages.</em>}</dd>
        <dt>Proposed call</dt>
        <dd>
          <pre>{`${data.tool}(${JSON.stringify(data.arguments, null, 2)})`}</pre>
        </dd>
      </dl>

      {message && (
        <p role={message.kind === 'error' ? 'alert' : 'status'} className={message.kind === 'error' ? 'error' : 'ok'}>
          {message.text}
        </p>
      )}

      {data.status === 'pending' && (
        <ReviewPanel
          escalation={data}
          reviewer={reviewer}
          busy={busy}
          onApprove={(note) => void decide(() => api.approve(id, reviewer.trim(), note))}
          onReject={(reason) => void decide(() => api.reject(id, reviewer.trim(), reason))}
        />
      )}

      <h3>History</h3>
      <ol className="timeline" aria-label="History">
        {data.events.map((event) => (
          <li key={event.seq}>
            <strong>{event.type.replaceAll('_', ' ')}</strong> by {event.actor}
            {event.note && <span>: {event.note}</span>}
          </li>
        ))}
      </ol>
    </article>
  )
}
