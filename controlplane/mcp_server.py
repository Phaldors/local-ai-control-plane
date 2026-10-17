"""MCP server for the shop tools, with the policy guard enforced on the server side.

Any MCP host (an agent framework, a desktop client) sees seven tools and a read-only escalation
queue. The guard decides every call from backend facts, so a careless or hijacked host cannot
bypass it. Two design points:

- There is deliberately **no approval tool**. A human approves an escalated refund out of band;
  if the model could call an "approve" tool it could approve its own escalation. The queue is
  exposed only as a read-only resource for a human-facing UI.
- The server sees tool arguments, not the user's messages, so the provenance rule (is this
  argument grounded in what the user wrote?) cannot run here. It has to live in the host.

Run over stdio:  python -m controlplane.mcp_server --guard rules --auth-customer C-1
"""

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from controlplane.audit import AuditLog
from controlplane.escalations import EscalationStore
from controlplane.guard import GuardedWorld, PolicyGuard
from controlplane.types import ToolCall
from controlplane.worlds.shop import ShopWorld

World = ShopWorld | GuardedWorld

INSTRUCTIONS = (
    "Customer-support tools for an online shop. Refunds are checked by a server-side policy: only "
    "delivered orders within 30 days, never above the order total; large refunds and "
    "unrequested actions may be held for a human. A held action is not executed."
)

Status = Literal["pending", "shipped", "delivered", "cancelled"]
Priority = Literal["low", "medium", "high"]


def build_server(world: World, name: str = "shop-control-plane") -> MCPServer:
    """One server per world. The world holds the state, the guard and the audit trail."""
    specs = {spec.name: spec for spec in world.specs}
    server = MCPServer(name, instructions=INSTRUCTIONS, log_level="WARNING")

    def run(tool: str, **arguments: Any) -> dict[str, Any]:
        return world.execute(ToolCall(name=tool, arguments=arguments))

    def describe(tool: str) -> str:
        return specs[tool].description

    def lookup_customer(email: str) -> dict:
        return run("lookup_customer", email=email)

    def search_orders(customer_id: str, status: Status | None = None) -> dict:
        arguments: dict[str, Any] = {"customer_id": customer_id}
        if status is not None:
            arguments["status"] = status
        return run("search_orders", **arguments)

    def get_order(order_id: str) -> dict:
        return run("get_order", order_id=order_id)

    def get_product(sku: str) -> dict:
        return run("get_product", sku=sku)

    def calculator(expression: str) -> dict:
        return run("calculator", expression=expression)

    def issue_refund(order_id: str, amount: float) -> dict:
        return run("issue_refund", order_id=order_id, amount=amount)

    def create_ticket(title: str, priority: Priority) -> dict:
        return run("create_ticket", title=title, priority=priority)

    for fn in (
        lookup_customer,
        search_orders,
        get_order,
        get_product,
        calculator,
        issue_refund,
        create_ticket,
    ):
        server.add_tool(fn, name=fn.__name__, description=describe(fn.__name__))

    escalations = getattr(world, "escalations", [])
    audit = getattr(getattr(world, "audit", None), "events", [])

    @server.resource("shop://escalations", mime_type="application/json")
    def pending_escalations() -> str:
        """Actions held for a human. Read-only: approval happens outside this server."""
        return json.dumps(escalations, ensure_ascii=False, indent=2)

    @server.resource("shop://audit", mime_type="application/json")
    def audit_trail() -> str:
        """Every guard decision so far (PII-redacted)."""
        return json.dumps(audit, ensure_ascii=False, indent=2)

    return server


def build_world(
    guard: str = "rules",
    auth_customer: str | None = None,
    audit_path: Path | None = None,
    escalation_db: Path | None = None,
) -> World:
    inner = ShopWorld()
    if guard == "off":
        return inner
    return GuardedWorld(
        inner,
        PolicyGuard(auth_customer_id=auth_customer),
        audit=AuditLog(audit_path),
        store=EscalationStore(escalation_db) if escalation_db else None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="controlplane.mcp_server")
    parser.add_argument("--guard", choices=["off", "rules"], default="rules")
    parser.add_argument(
        "--auth-customer", default=None, help="scope the session to one customer id"
    )
    parser.add_argument(
        "--audit-log", type=Path, default=None, help="append decisions to this JSONL"
    )
    parser.add_argument(
        "--escalation-db", type=Path, default=None, help="SQLite queue read by the review console"
    )
    args = parser.parse_args()
    world = build_world(args.guard, args.auth_customer, args.audit_log, args.escalation_db)
    build_server(world).run()


if __name__ == "__main__":
    main()
