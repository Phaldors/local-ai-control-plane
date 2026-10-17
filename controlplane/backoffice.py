"""Executes a human-approved escalation against the (demo) backend.

Approval clears only the "needs a human" part. Hard policy still applies at execution time: a refund
on an order that is not delivered, is outside the window or would exceed the order total is refused
even if a reviewer clicks approve. Only side-effecting tools can be executed here.
"""

from typing import Any

from controlplane.escalations import Escalation
from controlplane.guard import PolicyGuard
from controlplane.types import ToolCall
from controlplane.worlds.shop import ShopWorld

EXECUTABLE = {"issue_refund", "create_ticket"}


class BackOffice:
    def __init__(self, world: ShopWorld | None = None):
        self.world = world or ShopWorld()
        # A human has approved the high-value part; every other rule is still enforced.
        self._guard = PolicyGuard(escalate_refund_over=float("inf"))

    def check(self, escalation: Escalation) -> dict[str, Any] | None:
        """None if the action may be executed, otherwise why not."""
        if escalation.tool not in EXECUTABLE:
            return {
                "blocked_by": "tool_not_executable",
                "message": f"{escalation.tool} is read-only",
            }
        call = ToolCall(name=escalation.tool, arguments=escalation.arguments)
        decision = self._guard.check(call, self.world)
        if decision.action == "block":
            return {"blocked_by": decision.rule, "message": decision.reason}
        return None

    def execute(self, escalation: Escalation) -> dict[str, Any]:
        refusal = self.check(escalation)
        if refusal is not None:
            return {"executed": False, **refusal}
        result = self.world.execute(ToolCall(name=escalation.tool, arguments=escalation.arguments))
        return {"executed": "error" not in result, "result": result}
