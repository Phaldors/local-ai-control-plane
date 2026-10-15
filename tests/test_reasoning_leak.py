import json

import pytest

from controlplane.dashboard import trace_stats
from controlplane.gate import evaluate
from controlplane.reasoning import looks_like_leaked_reasoning
from controlplane.tracing import TracedClient, TraceSink
from controlplane.types import ChatRequest, ChatResult, Message
from tests.test_gate_dashboard import make_report


@pytest.mark.parametrize(
    "text",
    [
        "Okay, let's see. The user wants a refund for order O-1006 in full.",
        "Okay, so the user is asking about the status of an order. First, I need to check.",
        "Hmm, the user wants the weather. Let me check the tools available.",
        "Alright, let me think about this. I should call get_order first.",
        "\n\nOkay, the user is asking to refund. I need to get the order details.",
    ],
)
def test_detects_reasoning_openers(text):
    assert looks_like_leaked_reasoning(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        '{"total_price": "45,500", "subtotal_price": null, "item_count": 3}',
        "The status of order O-2001 is delivered.",
        "Okay, the order is pending.",
        "I'm sorry, but I can only access information for your own orders.",
        "Order O-1006 has been refunded. Let me know if you need anything else.",
        "A ticket (T-1) has been opened with medium priority.",
    ],
)
def test_does_not_flag_normal_answers(text):
    assert not looks_like_leaked_reasoning(text)


class Echo:
    runtime = "fake"

    def __init__(self, text):
        self.text = text

    def chat(self, request):
        return ChatResult(runtime="fake", model="m", text=self.text, latency_ms=1.0)


def request(think):
    return ChatRequest(model="m", messages=[Message(role="user", content="x")], think=think)


def test_traced_client_counts_leaks_only_for_think_off_calls(tmp_path):
    leaky = "Okay, let's see. The user wants a refund."
    client = TracedClient(Echo(leaky), TraceSink(tmp_path / "t.jsonl"), "r")
    client.chat(request(False))
    client.chat(request(False))
    client.chat(request(None))  # thinking default: reasoning is expected, not a leak
    client.chat(request(True))
    assert (client.think_off_calls, client.leaked_calls) == (2, 2)
    rows = [json.loads(line) for line in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert [r["reasoning_leak"] for r in rows] == [True, True, False, False]


def report_with_leak(leaked, calls=50, think=False):
    report = make_report()
    report["meta"]["think"] = think
    report["meta"]["reasoning_leak"] = {"think_off_calls": calls, "leaked": leaked}
    return report


def test_gate_fails_when_thinking_starts_leaking_and_warns_when_it_always_did():
    clean = report_with_leak(0)
    assert evaluate(report_with_leak(40), clean).status == "FAIL"
    assert evaluate(report_with_leak(3), clean).status == "PASS"  # 6% is under the limit
    always_leaky = report_with_leak(45)
    assert evaluate(report_with_leak(45), always_leaky).status == "WARN"


def test_gate_ignores_leak_rule_with_too_few_calls_or_thinking_not_off():
    clean = report_with_leak(0)
    assert evaluate(report_with_leak(5, calls=5), clean).status == "PASS"
    default = report_with_leak(0, calls=0, think=None)
    assert evaluate(default, default).status == "PASS"


def test_dashboard_leak_share_is_computed_from_traces_for_think_off_runs(tmp_path):
    rows = [
        {"status": "ok", "latency_ms": 1.0, "output": "Okay, let's see. The user wants it."},
        {"status": "ok", "latency_ms": 1.0, "output": "Order delivered."},
    ]
    (tmp_path / "traces.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    assert trace_stats(tmp_path, think_off=True)["leak"] == 0.5
    assert trace_stats(tmp_path, think_off=False)["leak"] is None
