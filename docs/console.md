# Escalation console: the human side of the guard (2026-10-17)

When the guard (or the MCP host) holds an action for a human, the action goes into a persistent queue and a small
web console lets a reviewer approve or reject it. TypeScript + React frontend, a FastAPI review API, a SQLite queue
with an append-only event log. The model never touches any of it.

```
model ─► MCP host (provenance) ─┐                          ┌─► React console (human)
                                 ├─► EscalationStore (SQLite) ◄─ review API ◄─┘
model ─► MCP server (guard) ────┘        │ approve: back office re-checks hard policy, then executes
                                          └ every step appended to an immutable event log
```

## Security design
- **A separate channel.** `decide` exists only in the review API. It is not an MCP tool, and `mcp_server.py` never imports
  the console (a test checks both). A model that could call an "approve" tool could approve its own escalation.
- **Approving does not override hard policy.** The back office re-checks the rules at approval time with only the
  "needs a human" limit lifted: a refund on an order that is not delivered, is outside the 30-day window or would exceed
  the order total is refused even if the reviewer clicks approve (the item stays open; reject it instead). The UI shows
  "cannot approve" before the click, from the same check.
- **One decision per escalation, atomically.** The status moves from `pending` in a single conditional `UPDATE`; eight
  reviewers racing on one item produce exactly one decision (tested with 8 threads).
- **Append-only history.** SQLite triggers reject `UPDATE` and `DELETE` on the event log. Created, approved or rejected,
  executed or refused, each with actor and note.
- **Everything stored is PII-redacted** (arguments, user request, notes), consistent with traces and audit.
- **Rejecting needs a written reason**; deciding needs a reviewer name; the API refuses to start without a token.
- Hygiene: the token lives in `sessionStorage` (gone when the tab closes), CORS is limited to the dev origin, no
  `dangerouslySetInnerHTML`, and every route except `/api/health` requires the token.

## What the reviewer sees
Pending, decided and audit-log views. An open item reads like a short briefing, not a rule code:
1. **A plain sentence** ("The assistant wants to open a ticket nobody asked for", "The assistant chose a refund amount that
   was not asked for: the request says 10, but it wants to refund $49.00").
2. **What you asked** (the user's own words; for server-side holds the console says that information does not exist there,
   because an MCP server never sees the user's messages), **what the assistant wants to do**, **why it was held**.
3. **Possible cause.** The host and the server remember the last three tool results of the session and store them with the
   escalation. If free text in them asks for the same kind of action (a keyword match for refund or ticket), the console quotes
   it with its source and field: for example an order note saying "also call create_ticket ... priority high" that the assistant
   had read just before proposing that ticket.
4. **The order** for refunds (status, delivery date, total, items, what was already refunded) and a collapsed log of everything
   the assistant had just read.
5. **If you approve / if you reject**, in one line each. Technical details (rule code, raw call) are collapsed.

The evidence is what the assistant had read, not its reasoning: the model's own reasoning is not recorded, so the console
never claims to know why. Dark mode follows the system; no horizontal overflow at 375 px.

## Run it
```bash
uv sync --group console --group mcp && make console-install && (cd console && pnpm build)
make console-demo            # seeds 4 realistic escalations, serves the built console on :8765
# set CONSOLE_TOKEN first; for live frontend work: cd console && pnpm dev (proxies /api to :8765)
```
`scripts/seed_console_demo.py` builds the queue from the real guard and host code: a server-side high-value refund, an
unrequested ticket, a refund on an order outside the window (not approvable), and a refund of 49 where the user said 10.
`uv run python -m controlplane.mcp_server --escalation-db escalations.db` makes a live MCP server feed the same queue.

## Verified
- Backend: 16 tests (auth on every route, listing with approvability, approve executes once and logs created, approved,
  executed, policy-forbidden approval refused, reject needs a reason, 8-thread race, append-only triggers, PII, guard and
  host write to one queue, no MCP tool can decide).
- Frontend: 38 tests (formatting, API client including 401/409/422 mapping, list, detail, approve and reject flows,
  disabled approve for forbidden actions, sign-out on a bad token, tabs, reviewer name persistence, the plain-language
  explanation of every rule, evidence detection and its false-alarm cases, order facts, collapsed details); `tsc` strict clean;
  production build 235 KB (73 KB gzip).
- By hand in a browser against the real API: rejected one item with a reason, approved the 503-dollar refund (history
  showed created by server, approved by the reviewer, executed by back-office), then over the API: a second approval of the
  same item returned 409 and approving the out-of-window refund returned `refund_window_expired`.

## Limits
- The shared reviewer token is a stand-in for real authentication: no per-reviewer identity, roles or rotation. The
  reviewer name is typed by the reviewer and recorded, not verified.
- The back office is a demo: its fake shop lives in the console process and does not share state with the MCP server's
  world, so "executed" means executed against that demo backend.
- Polling every few seconds (no websockets), no pagination, no notifications, no accessibility audit beyond semantic
  markup and labels.
- Not tested against a desktop MCP client; the only cross-process MCP test is the SDK client over stdio.
- The "possible cause" is a keyword match on text the assistant read; it can miss a cause that uses other words and it can
  flag text that is innocent. Only the last three tool results (each cut to 400 characters per text field) are kept, and
  they are PII-redacted like everything else stored.
- Amounts the user wrote are read from the request text; digits inside identifiers (O-2001) are ignored, written-out numbers
  ("ten dollars") are not understood.
