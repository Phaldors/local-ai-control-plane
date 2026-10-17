import { ApiError, AuthError, createApi } from './api'

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: 'x',
    json: async () => body,
  })
}

describe('api client', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('sends the reviewer token on every request and unwraps the list', async () => {
    const fetchMock = respond(200, { items: [{ id: 'ESC-0001' }] })
    vi.stubGlobal('fetch', fetchMock)
    const items = await createApi('secret').list('pending')
    expect(items).toEqual([{ id: 'ESC-0001' }])
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/escalations?status=pending')
    expect(init.headers['X-Reviewer-Token']).toBe('secret')
  })

  it('maps 401 to AuthError', async () => {
    vi.stubGlobal('fetch', respond(401, { detail: 'invalid reviewer token' }))
    await expect(createApi('bad').list()).rejects.toBeInstanceOf(AuthError)
  })

  it('surfaces the server message for a refused approval (409)', async () => {
    vi.stubGlobal('fetch', respond(409, { detail: 'cannot approve: refund_window_expired (too old)' }))
    const attempt = createApi('t').approve('ESC-1', 'arda')
    await expect(attempt).rejects.toBeInstanceOf(ApiError)
    await expect(attempt).rejects.toMatchObject({
      status: 409,
      message: expect.stringContaining('refund_window_expired'),
    })
  })

  it('turns validation errors (422 list) into one readable message', async () => {
    vi.stubGlobal('fetch', respond(422, { detail: [{ loc: ['body', 'reason'], msg: 'Field required' }] }))
    await expect(createApi('t').reject('ESC-1', 'arda', '')).rejects.toThrow('reason: Field required')
  })

  it('posts the reviewer and the reason when rejecting', async () => {
    const fetchMock = respond(200, { escalation: {} })
    vi.stubGlobal('fetch', fetchMock)
    await createApi('t').reject('ESC-1', 'arda', 'not requested')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/escalations/ESC-1/reject')
    expect(JSON.parse(init.body)).toEqual({ reviewer: 'arda', reason: 'not requested' })
  })
})
