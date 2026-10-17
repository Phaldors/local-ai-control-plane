import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Console } from './App'
import { AuthError } from './api'
import { detail, escalation, fakeApi } from './fixtures'

function open(api = fakeApi(), onSignOut = vi.fn()) {
  render(<Console api={api} onSignOut={onSignOut} pollMs={null} />)
  return { api, onSignOut }
}

describe('Console', () => {
  beforeEach(() => localStorage.clear())

  it('lists pending items and shows the count', async () => {
    open()
    expect(await screen.findByText('Refund $503.00 on order O-1008')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Pending \(1\)/ })).toBeInTheDocument()
    expect(screen.getByText('Select an item to review it.')).toBeInTheDocument()
  })

  it('says when nothing is waiting', async () => {
    open(fakeApi({ list: vi.fn().mockResolvedValue([]) }))
    expect(await screen.findByText('Nothing is waiting for a human.')).toBeInTheDocument()
  })

  it('shows the user request and the proposed call when an item is selected', async () => {
    const api = fakeApi({
      get: vi.fn().mockResolvedValue(detail({ source: 'host', user_request: 'What is in order O-1011?' })),
    })
    open(api)
    await userEvent.click(await screen.findByRole('button', { name: /Refund \$503\.00/ }))
    const view = await screen.findByRole('article')
    expect(within(view).getByText('What is in order O-1011?')).toBeInTheDocument()
    expect(within(view).getByText(/issue_refund\(/)).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('ESC-0001')
  })

  it('explains that a server-side hold has no user request', async () => {
    open()
    await userEvent.click(await screen.findByRole('button', { name: /Refund \$503\.00/ }))
    expect(await screen.findByText(/never sees the user's messages/)).toBeInTheDocument()
  })

  it('needs a reviewer name before anything can be decided', async () => {
    open()
    await userEvent.click(await screen.findByRole('button', { name: /Refund \$503\.00/ }))
    expect(await screen.findByText(/Enter your name/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve and execute' })).toBeDisabled()
  })

  it('approves with the reviewer name, refreshes and reports the execution', async () => {
    const { api } = open()
    await userEvent.type(screen.getByPlaceholderText('your name'), 'arda')
    await userEvent.click(await screen.findByRole('button', { name: /Refund \$503\.00/ }))
    await userEvent.type(await screen.findByLabelText('Approval note (optional)'), 'checked')
    await userEvent.click(screen.getByRole('button', { name: 'Approve and execute' }))
    expect(api.approve).toHaveBeenCalledWith('ESC-0001', 'arda', 'checked')
    expect(await screen.findByText('Approved and executed.')).toBeInTheDocument()
    await waitFor(() => expect(api.list).toHaveBeenCalledTimes(2))
  })

  it('cannot reject without a reason, then rejects with it', async () => {
    const { api } = open()
    await userEvent.type(screen.getByPlaceholderText('your name'), 'arda')
    await userEvent.click(await screen.findByRole('button', { name: /Refund \$503\.00/ }))
    const reject = await screen.findByRole('button', { name: 'Reject' })
    expect(reject).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Reason for rejecting'), 'user never asked')
    await userEvent.click(reject)
    expect(api.reject).toHaveBeenCalledWith('ESC-0001', 'arda', 'user never asked')
    expect(await screen.findByText('Rejected.')).toBeInTheDocument()
  })

  it('disables Approve for an action hard policy forbids, but still allows rejecting', async () => {
    const blocked = escalation({ approvable: false, blocked_by: 'refund_window_expired', blocked_message: 'delivered 106 days ago, window is 30' })
    open(fakeApi({ list: vi.fn().mockResolvedValue([blocked]), get: vi.fn().mockResolvedValue(detail(blocked)) }))
    await userEvent.type(screen.getByPlaceholderText('your name'), 'arda')
    expect(await screen.findByText('cannot approve')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Refund/ }))
    expect(await screen.findByRole('note')).toHaveTextContent('delivered 106 days ago')
    expect(screen.getByRole('button', { name: 'Approve and execute' })).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Reason for rejecting'), 'too old')
    expect(screen.getByRole('button', { name: 'Reject' })).toBeEnabled()
  })

  it('shows the server message when approval is refused (409)', async () => {
    const api = fakeApi({ approve: vi.fn().mockRejectedValue(Object.assign(new Error('cannot approve: refund_window_expired'), { status: 409 })) })
    open(api)
    await userEvent.type(screen.getByPlaceholderText('your name'), 'arda')
    await userEvent.click(await screen.findByRole('button', { name: /Refund \$503\.00/ }))
    await userEvent.click(await screen.findByRole('button', { name: 'Approve and execute' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('cannot approve: refund_window_expired')
  })

  it('signs out when the token stops being accepted', async () => {
    const { onSignOut } = open(fakeApi({ list: vi.fn().mockRejectedValue(new AuthError(401, 'Invalid reviewer token')) }))
    await waitFor(() => expect(onSignOut).toHaveBeenCalled())
  })

  it('moves decided items to their own tab', async () => {
    const decided = escalation({ id: 'ESC-0002', status: 'approved', tool: 'create_ticket', arguments: { title: 'Printer jam', priority: 'high' } })
    open(fakeApi({ list: vi.fn().mockResolvedValue([escalation(), decided]) }))
    await screen.findByText('Refund $503.00 on order O-1008')
    expect(screen.queryByText(/Printer jam/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Decided \(1\)/ }))
    expect(await screen.findByText(/Printer jam/)).toBeInTheDocument()
  })

  it('remembers the reviewer name between visits', async () => {
    open()
    await userEvent.type(screen.getByPlaceholderText('your name'), 'arda')
    expect(localStorage.getItem('console.reviewer')).toBe('arda')
  })
})
