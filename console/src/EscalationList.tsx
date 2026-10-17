import { RuleBadge, SourceBadge, StatusBadge } from './Badges'
import { describeAction, relativeTime } from './format'
import type { Escalation } from './types'

interface Props {
  items: Escalation[]
  selectedId: string | null
  onSelect: (id: string) => void
  emptyText: string
}

export function EscalationList({ items, selectedId, onSelect, emptyText }: Props) {
  if (items.length === 0) return <p className="empty">{emptyText}</p>
  return (
    <ul className="list" aria-label="Escalations">
      {items.map((item) => (
        <li key={item.id}>
          <button
            type="button"
            className={`card ${item.id === selectedId ? 'selected' : ''}`}
            aria-current={item.id === selectedId}
            onClick={() => onSelect(item.id)}
          >
            <span className="card-title">{describeAction(item)}</span>
            <span className="card-meta">
              <span>{item.id}</span>
              <span>{relativeTime(item.created_at)}</span>
            </span>
            <span className="card-badges">
              <RuleBadge rule={item.rule} />
              <SourceBadge source={item.source} />
              {item.status !== 'pending' && <StatusBadge status={item.status} />}
              {item.status === 'pending' && !item.approvable && <span className="badge warn">cannot approve</span>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}
