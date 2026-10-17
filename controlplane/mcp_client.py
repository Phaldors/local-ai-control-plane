"""Run the agent loop and the eval suites through the MCP protocol.

`McpWorld` has the same interface as `ShopWorld` / `GuardedWorld` (specs, execute, refunds, tickets,
escalations, audit), but every call goes through an MCP client talking to `build_server(world)`
in-process. Tool listing, argument validation, result encoding and error mapping are therefore the
real protocol paths, while the backend state stays inspectable for the eval oracle.

The agent loop is synchronous and the MCP client is async, so the client lives in its own thread
and event loop and is driven through a request queue (anyio requires the client context to be
entered and exited by the same task).
"""

import asyncio
import json
import threading
from concurrent.futures import Future
from typing import Any

from mcp.client import Client

from controlplane.audit import AuditLog
from controlplane.escalations import EscalationStore
from controlplane.guard import GuardedWorld, PolicyGuard
from controlplane.mcp_server import World, build_server
from controlplane.types import ToolCall, ToolSpec


class McpWorld:
    def __init__(
        self,
        inner: World,
        host_provenance: bool = False,
        store: EscalationStore | None = None,
    ):
        """`host_provenance`: the host (this adapter), not the server, escalates side-effecting
        calls whose arguments the user never wrote. The server cannot: it never sees the user."""
        self.inner = inner
        self.host_provenance = host_provenance
        self.store = store
        self._provenance = PolicyGuard(provenance=True)
        self._user_text = ""
        self.host_escalations: list[dict[str, Any]] = []
        self.name = f"{inner.name}+mcp"
        self.system_prompt = inner.system_prompt
        self._server = build_server(inner)
        self._loop = asyncio.new_event_loop()
        self._queue: asyncio.Queue | None = None
        self._ready: Future[list[ToolSpec]] = Future()
        self._thread = threading.Thread(target=self._run, daemon=True, name="mcp-client")
        self._thread.start()
        self.specs: list[ToolSpec] = self._ready.result(timeout=30)

    # --- the same state surface as the in-process worlds ---
    @property
    def refunds(self) -> list[dict[str, Any]]:
        return self.inner.refunds

    @property
    def tickets(self) -> list[dict[str, Any]]:
        return self.inner.tickets

    @property
    def escalations(self) -> list[dict[str, Any]]:
        return [*getattr(self.inner, "escalations", []), *self.host_escalations]

    @property
    def audit(self) -> AuditLog | None:
        return self.inner.audit if isinstance(self.inner, GuardedWorld) else None

    def observe_user(self, text: str) -> None:
        self._user_text = text  # held by the host; never sent to the server

    def execute(self, call: ToolCall) -> dict[str, Any]:
        if self.host_provenance:
            held = self._provenance.check_provenance(call, self._user_text)
            if held is not None:
                self.host_escalations.append(
                    {
                        "tool": call.name,
                        "arguments": call.arguments,
                        "rule": held.rule,
                        "by": "host",
                    }
                )
                escalation_id = f"HOST-ESC-{len(self.host_escalations)}"
                if self.store is not None:
                    escalation_id = self.store.create(
                        call.name,
                        call.arguments,
                        held.rule,
                        held.reason,
                        source="host",
                        user_request=self._user_text or None,
                    ).id
                return {
                    "status": "pending_human_approval",
                    "escalation_id": escalation_id,
                    "message": "Held by the host: the user did not ask for this. Not executed.",
                }
        future: Future[dict[str, Any]] = Future()
        self._loop.call_soon_threadsafe(self._queue.put_nowait, (call, future))  # type: ignore[union-attr]
        return future.result(timeout=120)

    def close(self) -> None:
        if self._thread.is_alive():
            self._loop.call_soon_threadsafe(self._queue.put_nowait, None)  # type: ignore[union-attr]
            self._thread.join(timeout=10)

    # --- the client thread ---
    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as exc:  # surface start-up failures to the constructor
            if not self._ready.done():
                self._ready.set_exception(exc)
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        self._queue = asyncio.Queue()
        async with Client(self._server) as client:
            listed = await client.list_tools()
            self._ready.set_result(
                [
                    ToolSpec(
                        name=t.name, description=t.description or "", parameters=t.input_schema
                    )
                    for t in listed.tools
                ]
            )
            while (item := await self._queue.get()) is not None:
                call, future = item
                try:
                    result = await client.call_tool(call.name, call.arguments)
                    future.set_result(_decode(result))
                except Exception as exc:
                    future.set_result({"error": f"mcp_error: {exc}"})


def _decode(result: Any) -> dict[str, Any]:
    """MCP result -> the dict the agent loop expects; protocol errors become {"error": ...}."""
    text = "".join(getattr(part, "text", "") for part in result.content)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {"error": text or "empty_result"} if result.is_error else {"result": text}
    if result.is_error and "error" not in value:
        return {"error": text}
    return value if isinstance(value, dict) else {"result": value}
