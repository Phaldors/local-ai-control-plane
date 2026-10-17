import type { Escalation } from './types'

export function money(value: unknown): string {
  const amount = Number(value)
  return Number.isFinite(amount) ? `$${amount.toFixed(2)}` : String(value)
}

/** One line a reviewer can read at a glance. */
export function describeAction(e: Pick<Escalation, 'tool' | 'arguments'>): string {
  const a = e.arguments
  if (e.tool === 'issue_refund') return `Refund ${money(a.amount)} on order ${String(a.order_id)}`
  if (e.tool === 'create_ticket') return `Open ${String(a.priority)} priority ticket "${String(a.title)}"`
  return `${e.tool}(${JSON.stringify(a)})`
}

const RULE_LABELS: Record<string, string> = {
  high_value_refund: 'High-value refund',
  ungrounded_order: 'Order not named by the user',
  ungrounded_amount: 'Amount not given by the user',
  ungrounded_ticket: 'Ticket not requested',
  ungrounded_priority: 'Priority differs from the request',
}

export function ruleLabel(rule: string): string {
  return RULE_LABELS[rule] ?? rule.replaceAll('_', ' ')
}

export function relativeTime(iso: string, now: Date = new Date()): string {
  const seconds = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours} h ago`
  return `${Math.round(hours / 24)} d ago`
}
