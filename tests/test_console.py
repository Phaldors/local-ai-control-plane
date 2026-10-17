import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("fastapi", reason="needs the optional console dependency group")

from fastapi.testclient import TestClient  # noqa: E402

from controlplane.backoffice import BackOffice  # noqa: E402
from controlplane.console_api import create_app  # noqa: E402
from controlplane.escalations import AlreadyDecided, EscalationStore, NotFound  # noqa: E402
from controlplane.guard import GuardedWorld, PolicyGuard  # noqa: E402
from controlplane.types import ToolCall  # noqa: E402
from controlplane.worlds.shop import ShopWorld  # noqa: E402

TOKEN = "test-token"
AUTH = {"X-Reviewer-Token": TOKEN}


@pytest.fixture
def store(tmp_path):
    return EscalationStore(tmp_path / "esc.db")


@pytest.fixture
def client(store):
    return TestClient(create_app(store, BackOffice(), TOKEN))


def hold_refund(store, order="O-1008", amount=503.0, user_request=None, source="server"):
    return store.create(
        "issue_refund",
        {"order_id": order, "amount": amount},
        "high_value_refund",
        "refunds above the limit need a human",
        source,
        user_request,
    )


def test_every_route_but_health_needs_the_token(client, store):
    esc = hold_refund(store)
    assert client.get("/api/health").status_code == 200
    for method, url in (
        ("get", "/api/escalations"),
        ("get", f"/api/escalations/{esc.id}"),
        ("post", f"/api/escalations/{esc.id}/approve"),
        ("get", "/api/events"),
    ):
        assert getattr(client, method)(url).status_code == 401
        assert (
            getattr(client, method)(url, headers={"X-Reviewer-Token": "wrong"}).status_code == 401
        )


def test_listing_shows_pending_items_with_their_context_and_approvability(client, store):
    hold_refund(store, user_request="Refund order O-1008 in full")
    hold_refund(store, order="O-1005", amount=10.0, source="host")  # refund window expired
    items = client.get("/api/escalations?status=pending", headers=AUTH).json()["items"]
    assert [i["approvable"] for i in items] == [True, False]
    assert items[0]["user_request"] == "Refund order O-1008 in full"
    assert items[1]["blocked_by"] == "refund_window_expired"


def test_approve_executes_the_action_once_and_logs_everything(client, store):
    esc = hold_refund(store)
    done = client.post(
        f"/api/escalations/{esc.id}/approve", headers=AUTH, json={"reviewer": "arda", "note": "ok"}
    )
    assert done.status_code == 200
    assert done.json()["result"]["result"]["status"] == "refunded"
    assert done.json()["escalation"]["status"] == "approved"
    again = client.post(
        f"/api/escalations/{esc.id}/approve", headers=AUTH, json={"reviewer": "arda"}
    )
    assert again.status_code == 409
    types = [
        e["type"] for e in client.get(f"/api/escalations/{esc.id}", headers=AUTH).json()["events"]
    ]
    assert types == ["created", "approved", "executed"]


def test_a_reviewer_cannot_approve_what_hard_policy_forbids(client, store):
    esc = hold_refund(store, order="O-1005", amount=10.0, source="host")
    refused = client.post(
        f"/api/escalations/{esc.id}/approve", headers=AUTH, json={"reviewer": "arda"}
    )
    assert refused.status_code == 409 and "refund_window_expired" in refused.json()["detail"]
    assert store.get(esc.id).status == "pending"  # stays open: reject it instead
    assert "approval_refused" in [e["type"] for e in store.events(esc.id)]
    assert (
        client.post(
            f"/api/escalations/{esc.id}/reject",
            headers=AUTH,
            json={"reviewer": "arda", "reason": "too old"},
        ).status_code
        == 200
    )


def test_reject_needs_a_reason_and_executes_nothing(client, store):
    esc = hold_refund(store)
    no_reason = client.post(
        f"/api/escalations/{esc.id}/reject", headers=AUTH, json={"reviewer": "a"}
    )
    assert no_reason.status_code == 422
    ok = client.post(
        f"/api/escalations/{esc.id}/reject", headers=AUTH, json={"reviewer": "a", "reason": "no"}
    )
    assert ok.json()["escalation"]["status"] == "rejected"
    assert [e["type"] for e in store.events(esc.id)] == ["created", "rejected"]


def test_unknown_id_and_bad_status_filter(client):
    assert client.get("/api/escalations/ESC-9999", headers=AUTH).status_code == 404
    assert client.get("/api/escalations?status=weird", headers=AUTH).status_code == 422


def test_two_reviewers_racing_decide_exactly_once(store):
    esc = hold_refund(store)
    barrier = threading.Barrier(8)

    def attempt(i):
        barrier.wait()
        try:
            store.decide(esc.id, "approved" if i % 2 else "rejected", f"r{i}", None)
            return "won"
        except AlreadyDecided:
            return "lost"

    with ThreadPoolExecutor(8) as pool:
        outcomes = list(pool.map(attempt, range(8)))
    assert outcomes.count("won") == 1
    assert len([e for e in store.events(esc.id) if e["type"] in ("approved", "rejected")]) == 1


def test_the_event_log_is_append_only(store, tmp_path):
    esc = hold_refund(store)
    raw = sqlite3.connect(tmp_path / "esc.db")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("UPDATE events SET actor='forged' WHERE escalation_id=?", (esc.id,))
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        raw.execute("DELETE FROM events")


def test_stored_text_is_pii_redacted(store):
    esc = store.create(
        "create_ticket",
        {"title": "call +90 532 111 22 33", "priority": "high"},
        "ungrounded_ticket",
        "mail alice@example.com",
        "host",
        "email me at alice@example.com",
    )
    stored = store.get(esc.id)
    assert "alice@example.com" not in str(stored.as_dict())
    assert "+90 532" not in str(stored.as_dict())
    store.decide(esc.id, "rejected", "r", "ping bob@example.com")
    assert "bob@example.com" not in str(store.events(esc.id))


def test_unknown_escalation_in_the_store_raises(store):
    with pytest.raises(NotFound):
        store.get("ESC-0001")
    with pytest.raises(NotFound):
        store.decide("ESC-0001", "approved", "r", None)


def test_guard_and_host_write_to_the_same_queue(store):
    world = GuardedWorld(ShopWorld(), PolicyGuard(), store=store)
    held = world.execute(
        ToolCall(name="issue_refund", arguments={"order_id": "O-1008", "amount": 503})
    )
    assert held["escalation_id"] == "ESC-0001"
    assert store.get("ESC-0001").source == "server"

    from controlplane.mcp_client import McpWorld  # needs the mcp group

    host = McpWorld(GuardedWorld(ShopWorld(), PolicyGuard()), host_provenance=True, store=store)
    try:
        host.observe_user("What is in order O-1011?")
        out = host.execute(
            ToolCall(name="create_ticket", arguments={"title": "x", "priority": "high"})
        )
    finally:
        host.close()
    assert out["escalation_id"] == "ESC-0002"
    item = store.get("ESC-0002")
    assert item.source == "host" and item.user_request == "What is in order O-1011?"


def test_the_model_cannot_reach_the_console_from_the_mcp_surface():
    """The MCP server imports the store only to *create* escalations; no tool decides them."""
    import controlplane.mcp_server as mcp_server

    names = {s.name for s in ShopWorld.specs}
    assert not any(w in n for n in names for w in ("approve", "reject", "decide"))
    assert "console_api" not in open(mcp_server.__file__).read()


def test_context_is_stored_redacted_and_shrunk(store):
    long_note = "x" * 900
    esc = store.create(
        "create_ticket",
        {"title": "t", "priority": "high"},
        "ungrounded_ticket",
        "r",
        "host",
        context=[
            {
                "tool": "get_order",
                "arguments": {"order_id": "O-1011"},
                "result": {"customer_note": long_note, "contact": "alice@example.com"},
            },
        ],
    )
    item = store.get(esc.id).context[0]
    assert item["tool"] == "get_order"
    assert len(item["result"]["customer_note"]) < 500 and item["result"]["customer_note"].endswith(
        "…"
    )
    assert "alice@example.com" not in str(item)


def test_a_queue_created_before_context_existed_is_migrated(tmp_path):
    db = tmp_path / "old.db"
    raw = sqlite3.connect(db)
    raw.executescript(
        "CREATE TABLE escalations (id TEXT PRIMARY KEY, created_at TEXT NOT NULL,"
        " tool TEXT NOT NULL, arguments TEXT NOT NULL, rule TEXT NOT NULL, reason TEXT NOT NULL,"
        " source TEXT NOT NULL, user_request TEXT, case_id TEXT,"
        " status TEXT NOT NULL DEFAULT 'pending');"
        "INSERT INTO escalations VALUES ('ESC-0001','2026-10-01T00:00:00+00:00','issue_refund',"
        "'{\"order_id\":\"O-1\",\"amount\":5}','high_value_refund','r','server',NULL,NULL,'pending');"
    )
    raw.commit()
    raw.close()
    migrated = EscalationStore(db)
    assert migrated.get("ESC-0001").context == []
    new = migrated.create(
        "issue_refund", {"order_id": "O-2", "amount": 9}, "r", "r", "host", context=[{"tool": "x"}]
    )
    assert migrated.get(new.id).context == [{"tool": "x"}]


def test_server_and_host_attach_what_the_assistant_had_just_read(store):
    world = GuardedWorld(ShopWorld(), PolicyGuard(), store=store)
    world.execute(ToolCall(name="get_order", arguments={"order_id": "O-1011"}))
    world.execute(ToolCall(name="issue_refund", arguments={"order_id": "O-1008", "amount": 503}))
    server_ctx = store.get("ESC-0001").context
    assert [c["tool"] for c in server_ctx] == ["get_order"]
    assert "customer_note" in server_ctx[0]["result"]

    from controlplane.mcp_client import McpWorld

    host = McpWorld(GuardedWorld(ShopWorld(), PolicyGuard()), host_provenance=True, store=store)
    try:
        host.observe_user("What is in order O-1011?")
        host.execute(ToolCall(name="get_order", arguments={"order_id": "O-1011"}))
        host.execute(ToolCall(name="create_ticket", arguments={"title": "x", "priority": "high"}))
    finally:
        host.close()
    ctx = store.get("ESC-0002").context
    assert ctx[-1]["tool"] == "get_order" and "customer_note" in ctx[-1]["result"]


def test_api_exposes_order_facts_for_refunds_and_none_for_tickets(client, store):
    refund = hold_refund(store, order="O-1008")
    ticket = store.create(
        "create_ticket", {"title": "t", "priority": "high"}, "ungrounded_ticket", "r", "host"
    )
    facts = client.get(f"/api/escalations/{refund.id}", headers=AUTH).json()["facts"]
    assert facts["order_found"] and facts["total"] == 503.0 and facts["status"] == "delivered"
    assert facts["items"] == ["2 x Monitor", "1 x Desk Lamp"]
    assert client.get(f"/api/escalations/{ticket.id}", headers=AUTH).json()["facts"] is None
    unknown = hold_refund(store, order="O-9999")
    assert client.get(f"/api/escalations/{unknown.id}", headers=AUTH).json()["facts"] == {
        "order_found": False
    }
