import { describeAction, money, relativeTime, ruleLabel } from './format'

describe('format', () => {
  it('describes a refund and a ticket in one readable line', () => {
    expect(describeAction({ tool: 'issue_refund', arguments: { order_id: 'O-1008', amount: 503 } })).toBe(
      'Refund $503.00 on order O-1008',
    )
    expect(describeAction({ tool: 'create_ticket', arguments: { title: 'Printer jam', priority: 'high' } })).toBe(
      'Open high priority ticket "Printer jam"',
    )
  })

  it('falls back to the raw call for unknown tools and keeps non-numeric amounts visible', () => {
    expect(describeAction({ tool: 'get_order', arguments: { order_id: 'O-1' } })).toBe('get_order({"order_id":"O-1"})')
    expect(money('lots')).toBe('lots')
    expect(money(49.5)).toBe('$49.50')
  })

  it('labels known rules and humanises unknown ones', () => {
    expect(ruleLabel('ungrounded_order')).toBe('Order not named by the user')
    expect(ruleLabel('some_new_rule')).toBe('some new rule')
  })

  it('formats elapsed time', () => {
    const now = new Date('2026-10-17T12:00:00Z')
    expect(relativeTime('2026-10-17T11:59:40Z', now)).toBe('just now')
    expect(relativeTime('2026-10-17T11:30:00Z', now)).toBe('30 min ago')
    expect(relativeTime('2026-10-17T07:00:00Z', now)).toBe('5 h ago')
    expect(relativeTime('2026-10-12T12:00:00Z', now)).toBe('5 d ago')
  })
})
