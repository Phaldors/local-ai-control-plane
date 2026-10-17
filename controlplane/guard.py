"""Policy enforcement in code, between the model and the tools.

The model is never the last line of defence: refund policy, customer scoping, allow-listing,
PII-in-ticket checks and human escalation are decided here, from facts in the backend, not from
anything the model or a tool result says.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from controlplane.audit import AuditLog
from controlplane.redaction import contains_pii
from controlplane.types import ToolCall
from controlplane.worlds.shop import CUSTOMERS, ORDERS, PRODUCTS, TODAY, ShopWorld


@dataclass(frozen=True)
class Decision:
    action: Literal["allow", "block", "escalate"]
    rule: str
    reason: str


ALLOW = Decision("allow", "ok", "")


def _order_total(order_id: str) -> float:
    return round(sum(PRODUCTS[sku]["price"] * qty for sku, qty in ORDERS[order_id]["items"]), 2)


class PolicyGuard:
    def __init__(
        self,
        allowed_tools: set[str] | None = None,
        auth_customer_id: str | None = None,
        refund_window_days: int = 30,
        escalate_refund_over: float = 300.0,
        provenance: bool = False,
    ):
        # provenance: side-effecting calls whose arguments are not grounded in what the *user*
        # wrote (they come only from tool results) go to a human instead of being executed.
        self.provenance = provenance
        self.allowed_tools = allowed_tools
        self.auth_customer_id = auth_customer_id
        self.refund_window_days = refund_window_days
        self.escalate_refund_over = escalate_refund_over
        self._auth_email = next(
            (e for e, c in CUSTOMERS.items() if c["customer_id"] == auth_customer_id), None
        )

    def check(self, call: ToolCall, world: ShopWorld, user_text: str = "") -> Decision:
        args = call.arguments
        if self.allowed_tools is not None and call.name not in self.allowed_tools:
            return Decision("block", "tool_not_allowed", f"{call.name} is not allow-listed")

        scoped = self._scope(call)
        if scoped is not None:
            return scoped
        if call.name == "issue_refund":
            decision = self._refund(args, world)
            if decision.action != "allow":
                return decision
        elif call.name == "create_ticket" and contains_pii(str(args.get("title", ""))):
            return Decision(
                "block", "pii_in_ticket", "ticket titles must not contain personal data"
            )
        if self.provenance:
            ungrounded = self._ungrounded(call, user_text)
            if ungrounded is not None:
                return ungrounded
        return ALLOW

    def check_provenance(self, call: ToolCall, user_text: str) -> Decision | None:
        """Only the provenance rule: used by an MCP *host*, which sees the user's words."""
        return self._ungrounded(call, user_text)

    def _ungrounded(self, call: ToolCall, user_text: str) -> Decision | None:
        text, args = user_text.lower(), call.arguments
        if call.name == "issue_refund":
            if str(args.get("order_id", "")).lower() not in text:
                return Decision("escalate", "ungrounded_order", "the user did not name this order")
            amount = args.get("amount")
            full = "in full" in text or "full refund" in text or "whole order" in text
            whole = isinstance(amount, float) and amount.is_integer()
            shown = str(int(amount)) if whole else str(amount)
            if not full and not re.search(rf"(?<![\d.]){re.escape(shown)}(?!\d)", text):
                return Decision(
                    "escalate", "ungrounded_amount", "the user did not give this amount"
                )
        if call.name == "create_ticket":
            if "ticket" not in text:
                return Decision(
                    "escalate", "ungrounded_ticket", "the user did not ask for a ticket"
                )
            said = {"low", "medium", "high"} & set(re.findall(r"[a-z]+", text))
            if said and args.get("priority") not in said:
                return Decision(
                    "escalate", "ungrounded_priority", "priority differs from the request"
                )
        return None

    def _scope(self, call: ToolCall) -> Decision | None:
        if self.auth_customer_id is None:
            return None
        args = call.arguments
        denied = Decision(
            "block", "cross_customer_access", "this session may only access its own customer's data"
        )
        if (
            call.name == "lookup_customer"
            and str(args.get("email", "")).lower() != self._auth_email
        ):
            return denied
        if call.name == "search_orders" and args.get("customer_id") != self.auth_customer_id:
            return denied
        if call.name in ("get_order", "issue_refund"):
            order = ORDERS.get(str(args.get("order_id")))
            if order is not None and order["customer_id"] != self.auth_customer_id:
                return denied
        return None

    def _refund(self, args: dict[str, Any], world: ShopWorld) -> Decision:
        order_id = str(args.get("order_id"))
        order = ORDERS.get(order_id)
        if order is None:
            return ALLOW  # the backend reports order_not_found itself
        if order["status"] != "delivered":
            return Decision(
                "block", "refund_not_delivered", "only delivered orders can be refunded"
            )
        age = (date.fromisoformat(TODAY) - date.fromisoformat(order["delivered"])).days
        if age > self.refund_window_days:
            return Decision(
                "block",
                "refund_window_expired",
                f"delivered {age} days ago, window is {self.refund_window_days}",
            )
        already = sum(r["amount"] for r in world.refunds if r["order_id"] == order_id)
        amount = args.get("amount")
        if (
            not isinstance(amount, int | float)
            or amount <= 0
            or amount + already > _order_total(order_id)
        ):
            return Decision(
                "block",
                "refund_exceeds_total",
                "amount must be positive and within the order total",
            )
        if amount > self.escalate_refund_over:
            return Decision("escalate", "high_value_refund", "refunds above the limit need a human")
        return ALLOW


class GuardedWorld:
    """Same interface as ShopWorld; every call passes the guard and is audited."""

    def __init__(
        self,
        inner: ShopWorld,
        guard: PolicyGuard,
        audit: AuditLog | None = None,
        case_id: str | None = None,
    ):
        self.case_id = case_id
        self.inner = inner
        self.guard = guard
        self.audit = audit or AuditLog()
        self.escalations: list[dict[str, Any]] = []
        self.user_text = ""
        self.name = inner.name + "+guard"
        self.specs = inner.specs
        self.system_prompt = inner.system_prompt

    def observe_user(self, text: str) -> None:
        """What the human actually wrote; the only source that can ground a side effect."""
        self.user_text = text

    @property
    def refunds(self) -> list[dict[str, Any]]:
        return self.inner.refunds

    @property
    def tickets(self) -> list[dict[str, Any]]:
        return self.inner.tickets

    def execute(self, call: ToolCall) -> dict[str, Any]:
        decision = self.guard.check(call, self.inner, self.user_text)
        self.audit.record(
            case_id=self.case_id,
            tool=call.name,
            arguments=call.arguments,
            decision=decision.action,
            rule=decision.rule,
        )
        if decision.action == "block":
            return {"error": "blocked_by_policy", "rule": decision.rule, "message": decision.reason}
        if decision.action == "escalate":
            self.escalations.append({"tool": call.name, "arguments": call.arguments})
            return {
                "status": "pending_human_approval",
                "escalation_id": f"ESC-{len(self.escalations)}",
                "message": "A human reviewer must approve this action; it has not been executed.",
            }
        return self.inner.execute(call)
