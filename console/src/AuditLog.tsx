import type { Api } from './api'
import { usePolling } from './usePolling'

export function AuditLog({ api }: { api: Api }) {
  const { data, error } = usePolling(() => api.events(), 10_000, 'audit')
  if (error && !data) return <p role="alert" className="error">Could not load the audit log: {error.message}</p>
  if (!data) return <p className="empty">Loading…</p>
  if (data.length === 0) return <p className="empty">No events yet.</p>
  return (
    <table className="audit" aria-label="Audit log">
      <thead>
        <tr>
          <th>#</th>
          <th>Time (UTC)</th>
          <th>Escalation</th>
          <th>Event</th>
          <th>Actor</th>
          <th>Note</th>
        </tr>
      </thead>
      <tbody>
        {[...data].reverse().map((e) => (
          <tr key={e.seq}>
            <td>{e.seq}</td>
            <td>{e.ts.slice(0, 19).replace('T', ' ')}</td>
            <td>{e.escalation_id}</td>
            <td>{e.type.replaceAll('_', ' ')}</td>
            <td>{e.actor}</td>
            <td>{e.note ?? ''}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
