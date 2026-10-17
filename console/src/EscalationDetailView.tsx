import { useState } from 'react'
import type { Api } from './api'
import { RuleBadge, SourceBadge, StatusBadge } from './Badges'
import { EvidenceBanner, OrderFacts, ReadLog } from './EvidencePanel'
import { explain } from './explain'
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
        text: executed
          ? executed.executed
            ? 'Approved and executed.'
            : `Approved, but not executed: ${executed.message ?? 'see log'}`
          : 'Rejected.',
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

  const story = explain(data)

  return (
    <article className="detail" aria-label={`Escalation ${data.id}`}>
      <header>
        <h2>{story.headline}</h2>
        <div className="card-badges">
          <StatusBadge status={data.status} />
          <RuleBadge rule={data.rule} />
          <SourceBadge source={data.source} />
        </div>
      </header>

      <dl className="story">
        <dt>What you asked</dt>
        <dd>
          {story.asked ? (
            <q>{story.asked}</q>
          ) : (
            <em>Not available: the server holding this action never sees the user's messages.</em>
          )}
        </dd>
        <dt>What the assistant wants to do</dt>
        <dd>
          <strong>{story.wants}</strong>
        </dd>
        <dt>Why it was held</dt>
        <dd>{story.why}</dd>
      </dl>

      <EvidenceBanner escalation={data} />
      <OrderFacts escalation={data} />
      <ReadLog escalation={data} />

      <section className="outcomes" aria-label="Outcomes">
        <p>
          <strong>If you approve:</strong> {story.ifApprove}
        </p>
        <p>
          <strong>If you reject:</strong> {story.ifReject}
        </p>
      </section>

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

      <details className="technical">
        <summary>Technical details</summary>
        <p>
          Rule: <code>{data.rule}</code> ({data.reason})
        </p>
        <pre>{`${data.tool}(${JSON.stringify(data.arguments, null, 2)})`}</pre>
      </details>

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
