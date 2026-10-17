import type { Api } from './api'
import type { Escalation, EscalationDetail } from './types'

export function escalation(over: Partial<Escalation> = {}): Escalation {
  return {
    id: 'ESC-0001',
    created_at: new Date(Date.now() - 5 * 60_000).toISOString(),
    tool: 'issue_refund',
    arguments: { order_id: 'O-1008', amount: 503 },
    rule: 'high_value_refund',
    reason: 'refunds above the limit need a human',
    source: 'server',
    user_request: null,
    case_id: null,
    status: 'pending',
    approvable: true,
    blocked_by: null,
    blocked_message: null,
    ...over,
  }
}

export function detail(over: Partial<EscalationDetail> = {}): EscalationDetail {
  return {
    ...escalation(),
    events: [{ seq: 1, escalation_id: 'ESC-0001', ts: '2026-10-17T20:00:00+00:00', type: 'created', actor: 'server', note: null, details: null }],
    ...over,
  }
}

/** A fake API: every method is a spy, defaults return one pending escalation. */
export function fakeApi(over: Partial<Record<keyof Api, unknown>> = {}): Api {
  return {
    list: vi.fn().mockResolvedValue([escalation()]),
    get: vi.fn().mockResolvedValue(detail()),
    approve: vi.fn().mockResolvedValue({ escalation: escalation({ status: 'approved' }), result: { executed: true } }),
    reject: vi.fn().mockResolvedValue({ escalation: escalation({ status: 'rejected' }) }),
    events: vi.fn().mockResolvedValue([]),
    ...over,
  } as unknown as Api
}
