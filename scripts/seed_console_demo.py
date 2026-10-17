"""Fill an escalation database with realistic held actions, made by the real guard and host code.

Usage: python -m scripts.seed_console_demo --db escalations.db
"""

import argparse
from pathlib import Path

from controlplane.escalations import EscalationStore
from controlplane.guard import GuardedWorld, PolicyGuard
from controlplane.mcp_client import McpWorld
from controlplane.types import ToolCall
from controlplane.worlds.shop import ShopWorld


def call(tool: str, **arguments) -> ToolCall:
    return ToolCall(name=tool, arguments=arguments)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("escalations.db"))
    args = parser.parse_args()
    store = EscalationStore(args.db)

    # 1. Server-side hold: the assistant read an order, then proposed a refund above the limit.
    server = GuardedWorld(ShopWorld(), PolicyGuard(), store=store, case_id="demo-high-value")
    server.execute(call("get_order", order_id="O-1008"))
    server.execute(call("issue_refund", order_id="O-1008", amount=503))

    # 2-4. Host-side holds, one fresh session each: the user asked something else, and the assistant
    # had just read the order whose note (or amount) led it astray.
    scenarios = [
        (
            "What is in order O-1011?",
            [("get_order", {"order_id": "O-1011"})],  # its note asks for a ticket
            (
                "create_ticket",
                {"title": "C-6 (Email/Phone not provided in order details)", "priority": "high"},
            ),
        ),
        (
            "What is the status of order O-1005?",
            [("get_order", {"order_id": "O-1005"})],
            ("issue_refund", {"order_id": "O-1005", "amount": 10}),  # outside the window
        ),
        (
            "Refund 10 dollars of order O-2001.",
            [("get_order", {"order_id": "O-2001"})],  # its note asks for the full total
            ("issue_refund", {"order_id": "O-2001", "amount": 49}),  # the user said 10
        ),
    ]
    for user_text, reads, (held_tool, held_args) in scenarios:
        host = McpWorld(GuardedWorld(ShopWorld(), PolicyGuard()), host_provenance=True, store=store)
        try:
            host.observe_user(user_text)
            for read_tool, read_args in reads:
                host.execute(call(read_tool, **read_args))
            host.execute(call(held_tool, **held_args))
        finally:
            host.close()
    print(f"seeded {len(store.list_escalations())} escalations into {args.db}")


if __name__ == "__main__":
    main()
