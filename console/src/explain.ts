import { money } from './format'
import type { ContextItem, Escalation } from './types'

export interface Explanation {
  headline: string
  asked: string | null
  wants: string
  why: string
  ifApprove: string
  ifReject: string
}

type Held = Pick<Escalation, 'tool' | 'arguments' | 'rule' | 'reason' | 'user_request'>

function wants(e: Held): string {
  const a = e.arguments
  if (e.tool === 'issue_refund') return `Refund ${money(a.amount)} on order ${String(a.order_id)}`
  if (e.tool === 'create_ticket') return `Open a ${String(a.priority)} priority ticket titled "${String(a.title)}"`
  return `${e.tool}(${JSON.stringify(a)})`
}

function approveEffect(e: Held): string {
  const a = e.arguments
  if (e.tool === 'issue_refund') return `${money(a.amount)} is refunded on order ${String(a.order_id)}.`
  if (e.tool === 'create_ticket') return `A ${String(a.priority)} priority ticket is created.`
  return 'The action is carried out.'
}

/**
 * Amounts the user wrote ("$10", "10 dollars"), so a mismatch with the proposed amount is visible.
 * Digits that belong to an identifier ("O-2001", "SKU-A100") are not amounts.
 */
export function mentionedAmounts(text: string | null): string[] {
  return text ? [...text.matchAll(/(?<![\w-])\$?\d+(?:\.\d+)?(?![\w-])/g)].map((m) => m[0]) : []
}

export function explain(e: Held): Explanation {
  const base = {
    asked: e.user_request,
    wants: wants(e),
    ifApprove: approveEffect(e),
    ifReject: 'Nothing is executed. The assistant is told the action is on hold, not that it was refused.',
  }
  const a = e.arguments
  switch (e.rule) {
    case 'ungrounded_ticket':
      return {
        ...base,
        headline: 'The assistant wants to open a ticket nobody asked for',
        why: 'The request does not mention a ticket at all.',
      }
    case 'ungrounded_priority':
      return {
        ...base,
        headline: 'The ticket priority is not the one that was asked for',
        why: `The request named a different priority than "${String(a.priority)}".`,
      }
    case 'ungrounded_order':
      return {
        ...base,
        headline: 'The assistant wants to refund an order the request did not mention',
        why: `The request never names order ${String(a.order_id)}.`,
      }
    case 'ungrounded_amount': {
      const said = mentionedAmounts(e.user_request)
      return {
        ...base,
        headline: 'The assistant chose a refund amount that was not asked for',
        why: said.length
          ? `The request says ${said.join(' and ')}, but the assistant wants to refund ${money(a.amount)}.`
          : `The request does not give the amount ${money(a.amount)}.`,
      }
    }
    case 'high_value_refund':
      return {
        ...base,
        headline: 'A large refund is waiting for a human decision',
        why: 'Refunds above the automatic limit always need a person, even when the rules allow them.',
      }
    default:
      return { ...base, headline: wants(e), why: e.reason }
  }
}

export interface Evidence {
  tool: string
  source: string
  field: string
  text: string
}

const KEYWORDS: Record<string, RegExp> = {
  issue_refund: /refund/i,
  create_ticket: /ticket/i,
}

function* strings(value: unknown, path: string[] = []): Generator<[string, string]> {
  if (typeof value === 'string') yield [path.join('.'), value]
  else if (Array.isArray(value)) for (const [i, v] of value.entries()) yield* strings(v, [...path, String(i)])
  else if (value && typeof value === 'object')
    for (const [k, v] of Object.entries(value)) yield* strings(v, [...path, k])
}

/**
 * Free text the assistant had just read that asks for the same kind of action. This is a keyword match
 * on the evidence, not a verdict: it shows the reviewer what to look at.
 */
export function findEvidence(e: Pick<Escalation, 'tool' | 'context'>): Evidence[] {
  const pattern = KEYWORDS[e.tool]
  if (!pattern) return []
  const found: Evidence[] = []
  for (const item of e.context as ContextItem[]) {
    for (const [field, text] of strings(item.result)) {
      if (text.length >= 20 && pattern.test(text)) {
        found.push({ tool: item.tool, source: describeRead(item), field, text })
      }
    }
  }
  return found
}

export function describeRead(item: ContextItem): string {
  const arg = Object.values(item.arguments)[0]
  return arg === undefined ? item.tool : `${item.tool} ${String(arg)}`
}
