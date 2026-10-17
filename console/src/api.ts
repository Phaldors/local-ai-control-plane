import type { DecisionResult, Escalation, EscalationDetail, EscalationEvent, Status } from './types'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** The reviewer token was missing or wrong: the UI should go back to the sign-in screen. */
export class AuthError extends ApiError {}

function detailMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc: [...], msg: "..."}]
    return detail.map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.at(-1) ?? 'field'}: ${d.msg}`).join('; ')
  }
  return fallback
}

export function createApi(token: string, baseUrl = '') {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', 'X-Reviewer-Token': token, ...init.headers },
    })
    if (response.status === 401) throw new AuthError(401, 'Invalid reviewer token')
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new ApiError(response.status, detailMessage(body, response.statusText))
    }
    return (await response.json()) as T
  }

  return {
    async list(status?: Status): Promise<Escalation[]> {
      const query = status ? `?status=${status}` : ''
      return (await request<{ items: Escalation[] }>(`/api/escalations${query}`)).items
    },
    get: (id: string) => request<EscalationDetail>(`/api/escalations/${id}`),
    approve: (id: string, reviewer: string, note?: string) =>
      request<DecisionResult>(`/api/escalations/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ reviewer, note: note || null }),
      }),
    reject: (id: string, reviewer: string, reason: string) =>
      request<DecisionResult>(`/api/escalations/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reviewer, reason }),
      }),
    async events(): Promise<EscalationEvent[]> {
      return (await request<{ events: EscalationEvent[] }>('/api/events')).events
    },
  }
}

export type Api = ReturnType<typeof createApi>
