import { ruleLabel } from './format'
import type { Escalation } from './types'

export function StatusBadge({ status }: { status: Escalation['status'] }) {
  return <span className={`badge status-${status}`}>{status}</span>
}

export function SourceBadge({ source }: { source: Escalation['source'] }) {
  const text = source === 'host' ? 'held by host' : 'held by server'
  return <span className="badge source">{text}</span>
}

export function RuleBadge({ rule }: { rule: string }) {
  return <span className="badge rule">{ruleLabel(rule)}</span>
}
