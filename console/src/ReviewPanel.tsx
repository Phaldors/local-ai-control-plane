import { useState } from 'react'
import type { Escalation } from './types'

interface Props {
  escalation: Escalation
  reviewer: string
  busy: boolean
  onApprove: (note: string) => void
  onReject: (reason: string) => void
}

/** Approve is blocked when hard policy forbids the action; rejecting always needs a written reason. */
export function ReviewPanel({ escalation, reviewer, busy, onApprove, onReject }: Props) {
  const [note, setNote] = useState('')
  const [reason, setReason] = useState('')
  const needsName = reviewer.trim().length === 0

  return (
    <section className="review" aria-label="Review">
      {needsName && <p className="hint">Enter your name in the header before deciding.</p>}
      {!escalation.approvable && (
        <p role="note" className="blocked">
          Cannot be approved: {escalation.blocked_message ?? escalation.blocked_by}. You can still reject it.
        </p>
      )}
      <div className="review-grid">
        <div>
          <label htmlFor="note">Approval note (optional)</label>
          <input id="note" value={note} onChange={(e) => setNote(e.target.value)} />
          <button
            type="button"
            className="primary"
            disabled={busy || needsName || !escalation.approvable}
            onClick={() => onApprove(note)}
          >
            Approve and execute
          </button>
        </div>
        <div>
          <label htmlFor="reason">Reason for rejecting</label>
          <textarea id="reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          <button
            type="button"
            className="danger"
            disabled={busy || needsName || reason.trim().length === 0}
            onClick={() => onReject(reason.trim())}
          >
            Reject
          </button>
        </div>
      </div>
    </section>
  )
}
