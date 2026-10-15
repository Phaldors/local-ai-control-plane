import json
from pathlib import Path

from controlplane.agent import run_agent
from controlplane.evals.agent_scorer import score_agent
from controlplane.evals.contract import GoldenCase, load_cases
from controlplane.runtimes.mlx import _message as mlx_message
from controlplane.runtimes.ollama import _message as ollama_message
from controlplane.types import ChatRequest, ChatResult, Message, ToolCall
from controlplane.worlds.shop import ShopWorld


def call(name: str, **arguments) -> ToolCall:
    return ToolCall(name=name, arguments=arguments)


class ScriptedClient:
    """Replays a fixed list of model turns; each turn is a list of tool calls or final text."""

    runtime = "fake"

    def __init__(self, turns: list):
        self.turns = list(turns)
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResult:
        self.requests.append(request)
        turn = self.turns.pop(0)
        if isinstance(turn, ChatResult):
            return turn
        if isinstance(turn, str):
            return ChatResult(runtime="fake", model="m", text=turn, latency_ms=1.0)
        return ChatResult(runtime="fake", model="m", text="", tool_calls=turn, latency_ms=1.0)


def agent_case(**expected) -> GoldenCase:
    return GoldenCase(
        id="a",
        task="agent",
        world="shop-v1",
        messages=[Message(role="user", content="x")],
        expected=expected,
    )


def run(turns: list, **kw):
    return run_agent(
        ScriptedClient(turns), "m", [Message(role="user", content="x")], ShopWorld(), **kw
    )


def execute(name: str, **arguments) -> dict:
    return ShopWorld().execute(call(name, **arguments))


def test_world_numbers_behind_the_golden_labels():
    assert execute("get_order", order_id="O-1002")["total"] == 229.0
    assert execute("get_order", order_id="O-1003")["total"] == 108.0
    assert execute("get_order", order_id="O-1008")["total"] == 503.0
    assert execute("get_order", order_id="O-1006")["total"] == 118.0
    alice_all = sum(
        execute("get_order", order_id=o)["total"] for o in ("O-1001", "O-1002", "O-1003")
    )
    assert alice_all == 451.5
    assert (
        execute("get_order", order_id="O-1005")["total"]
        - execute("get_order", order_id="O-1001")["total"]
        == 114.5
    )
    assert execute("calculator", expression="2*3+1")["result"] == 7
    assert execute("get_order", order_id="nope") == {"error": "order_not_found"}


def test_loop_feeds_tool_results_back_and_finishes():
    client = ScriptedClient([[call("get_order", order_id="O-1004")], "It is shipped."])
    out = run_agent(client, "m", [Message(role="user", content="x")], ShopWorld())
    assert out.ended == "answered" and out.final_text == "It is shipped."
    second_request = client.requests[1].messages
    assert (
        second_request[-2].role == "assistant" and second_request[-2].tool_calls[0].id == "call_1"
    )
    assert second_request[-1].role == "tool" and "shipped" in second_request[-1].content


def test_loop_reports_step_limit():
    turns = [[call("get_product", sku="SKU-A100")]] * 3
    assert run(turns, max_turns=3).ended == "step_limit"


def test_unknown_tool_and_bad_args_are_flagged_not_fatal():
    out = run([[call("send_email", to="x")], [call("get_order", order_id=5)], "done"])
    assert [s.flags for s in out.steps] == [["hallucinated_tool"], ["bad_args_schema"]]
    assert out.ended == "answered"


def test_scorer_passes_correct_chain():
    out = run(
        [
            [call("lookup_customer", email="alice@example.com")],
            [call("get_order", order_id="O-1002")],
            "Total 229",
        ]
    )
    case = agent_case(
        required_calls=[{"tool": "get_order", "arguments": {"order_id": "O-1002"}}],
        answer_any=[["229"]],
        depth=2,
        max_tool_calls=6,
    )
    assert score_agent(case, out).passed


def test_scorer_flags_forbidden_refund_even_if_answer_looks_fine():
    out = run([[call("issue_refund", order_id="O-1005", amount=229)], "Refunded, sorry!"])
    case = agent_case(forbidden_tools=["issue_refund"], answer_any=[["refund"]])
    result = score_agent(case, out)
    assert result.failure == "forbidden_call" and out.refunds


def test_scorer_missing_required_call_and_wrong_answer():
    out = run([[call("get_order", order_id="O-1001")], "It is 5"])
    missing = agent_case(
        required_calls=[{"tool": "get_order", "arguments": {"order_id": "O-1002"}}]
    )
    assert score_agent(missing, out).failure == "missing_required_call"
    wrong = agent_case(answer_any=[["229"]])
    assert score_agent(wrong, out).failure == "wrong_answer"


def test_scorer_no_tools_case():
    case = agent_case(no_tools=True)
    assert score_agent(case, run(["Which order?"])).passed
    assert (
        score_agent(case, run([[call("get_product", sku="SKU-A100")], "ok"])).failure
        == "unexpected_call"
    )


def test_scorer_numbers_with_thousands_separator_and_currency():
    out = run(["The total is $1,234.50"])
    assert score_agent(agent_case(answer_any=[["1234.5"]]), out).passed


def test_scorer_truncation_and_inefficiency():
    client = ScriptedClient(
        [ChatResult(runtime="fake", model="m", text="", latency_ms=1.0, finish_reason="length")]
    )
    truncated = run_agent(client, "m", [Message(role="user", content="x")], ShopWorld())
    assert score_agent(agent_case(), truncated).failure == "truncated"
    wasteful = run([[call("get_product", sku="SKU-A100")]] * 3 + ["done"])
    assert score_agent(agent_case(max_tool_calls=2), wasteful).failure == "inefficient"


def test_runtime_message_formats_for_tool_turns():
    assistant = Message(
        role="assistant",
        tool_calls=[ToolCall(name="get_order", arguments={"order_id": "O-1"}, id="call_1")],
    )
    tool = Message(role="tool", content="{}", tool_name="get_order", tool_call_id="call_1")
    assert ollama_message(assistant)["tool_calls"][0]["function"]["arguments"] == {
        "order_id": "O-1"
    }
    assert ollama_message(tool)["tool_name"] == "get_order"
    mlx_call = mlx_message(assistant)["tool_calls"][0]
    assert mlx_call["id"] == "call_1" and json.loads(mlx_call["function"]["arguments"]) == {
        "order_id": "O-1"
    }
    assert mlx_message(tool)["tool_call_id"] == "call_1"


def test_golden_agent_cases_are_consistent_with_the_world():
    cases = load_cases(Path("golden/agent.jsonl"))
    assert len(cases) >= 25
    skus = {"SKU-A100", "SKU-B200", "SKU-C300", "SKU-D400", "SKU-E500"}
    for case in cases:
        for wanted in case.expected.get("required_calls", []):
            assert wanted["tool"] in {s.name for s in ShopWorld.specs}
            if wanted["tool"] == "get_product":
                assert wanted["arguments"]["sku"] in skus


def test_test_split_is_disjoint_from_validation_and_its_labels_match_the_world():
    from collections import Counter

    for name in ("extraction", "tool_call", "multi_extraction", "agent", "agent_security"):
        cases = load_cases(Path(f"golden/{name}.jsonl"))
        ids = Counter(c.id for c in cases)
        assert max(ids.values()) == 1, f"duplicate ids in {name}"
        validation = {c.messages[-1].content for c in cases if c.split == "validation"}
        test = {c.messages[-1].content for c in cases if c.split == "test"}
        assert test and not (validation & test), f"{name}: test prompts overlap validation"

    totals = {
        "O-1001": 114.5,
        "O-1006": 118.0,
        "O-1008": 503.0,
        "O-1014": 517.0,
        "O-1007": 45.0,
        "O-1016": 49.0,
    }
    for order_id, expected in totals.items():
        assert execute("get_order", order_id=order_id)["total"] == expected
    assert totals["O-1001"] + totals["O-1008"] == 617.5
