import { describeRead, findEvidence } from './explain'
import { money } from './format'
import type { Escalation } from './types'

/** Free text the assistant had just read that asks for this very action: shown as a quote, not a verdict. */
export function EvidenceBanner({ escalation }: { escalation: Escalation }) {
  const evidence = findEvidence(escalation)
  if (evidence.length === 0) return null
  return (
    <aside className="evidence" aria-label="Possible cause">
      <strong>The assistant had just read text that asks for this action.</strong>
      <p>
        Text inside data is not written by you. Check whether the action follows from it rather than from your request.
      </p>
      {evidence.map((item) => (
        <blockquote key={`${item.source}.${item.field}`}>
          “{item.text}”
          <footer>
            from {item.source}, field <code>{item.field}</code>
          </footer>
        </blockquote>
      ))}
    </aside>
  )
}

export function OrderFacts({ escalation }: { escalation: Escalation }) {
  const facts = escalation.facts
  if (!facts) return null
  if (!facts.order_found) return <p className="blocked">This order does not exist in the backend.</p>
  return (
    <section aria-label="Order facts" className="order-facts">
      <h3>The order</h3>
      <p>
        {String(escalation.arguments.order_id)}: <strong>{facts.status}</strong>
        {facts.delivered ? `, delivered ${facts.delivered}` : `, placed ${facts.placed}`}; total {money(facts.total)}
        {facts.already_refunded ? `; already refunded ${money(facts.already_refunded)}` : ''}
      </p>
      <p className="muted">{facts.items?.join(', ')}</p>
    </section>
  )
}

export function ReadLog({ escalation }: { escalation: Escalation }) {
  if (escalation.context.length === 0) return null
  return (
    <details className="read-log">
      <summary>What the assistant had just read ({escalation.context.length})</summary>
      <ol>
        {escalation.context.map((item, index) => (
          <li key={index}>
            <strong>{describeRead(item)}</strong>
            <pre>{JSON.stringify(item.result, null, 2)}</pre>
          </li>
        ))}
      </ol>
    </details>
  )
}
