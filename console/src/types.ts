export type Status = 'pending' | 'approved' | 'rejected'

export interface ContextItem {
  tool: string
  arguments: Record<string, unknown>
  result: Record<string, unknown>
}

export interface OrderFacts {
  order_found: boolean
  status?: string
  placed?: string
  delivered?: string | null
  total?: number
  already_refunded?: number
  items?: string[]
}

export interface Escalation {
  id: string
  created_at: string
  tool: string
  arguments: Record<string, unknown>
  rule: string
  reason: string
  /** "server": the guard behind the tools held it. "host": provenance in the MCP host held it. */
  source: 'server' | 'host'
  user_request: string | null
  case_id: string | null
  status: Status
  /** Only meaningful while pending: false means hard policy would refuse the action even if approved. */
  approvable: boolean
  blocked_by: string | null
  blocked_message: string | null
  /** What the assistant had just read (recent tool results): evidence, not a stated reason. */
  context: ContextItem[]
  /** Backend facts about the order for refunds, null for other actions. */
  facts: OrderFacts | null
}

export interface EscalationEvent {
  seq: number
  escalation_id: string
  ts: string
  type: string
  actor: string
  note: string | null
  details: Record<string, unknown> | null
}

export interface EscalationDetail extends Escalation {
  events: EscalationEvent[]
}

export interface DecisionResult {
  escalation: Escalation
  result?: { executed: boolean; result?: Record<string, unknown>; message?: string }
}
