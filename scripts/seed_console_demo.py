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

    # 1. Server-side hold: an eligible refund above the auto-approval limit.
    server = GuardedWorld(ShopWorld(), PolicyGuard(), store=store, case_id="demo-high-value")
    server.execute(call("issue_refund", order_id="O-1008", amount=503))

    # 2-4. Host-side holds: the model asked for actions the user never asked for.
    host = McpWorld(GuardedWorld(ShopWorld(), PolicyGuard()), host_provenance=True, store=store)
    try:
        host.observe_user("What is in order O-1011?")
        host.execute(call("create_ticket", title="C-6 follow up needed", priority="high"))

        host.observe_user("What is the status of order O-1005?")
        host.execute(call("issue_refund", order_id="O-1005", amount=10))  # outside the window

        host.observe_user("Refund 10 dollars of order O-2001.")
        host.execute(
            call("issue_refund", order_id="O-2001", amount=49)
        )  # user said 10, model said 49
    finally:
        host.close()
    print(f"seeded {len(store.list_escalations())} escalations into {args.db}")


if __name__ == "__main__":
    main()
