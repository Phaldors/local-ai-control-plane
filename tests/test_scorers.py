from controlplane.evals.contract import GoldenCase
from controlplane.evals.scorers import score_extraction, score_tool_call
from controlplane.types import ChatResult, Message, ToolCall, ToolSpec

WEATHER = ToolSpec(
    name="get_weather",
    description="weather",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    },
)
CALC = ToolSpec(
    name="calculator",
    description="calc",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
)


def result(text: str = "", calls: list[ToolCall] | None = None) -> ChatResult:
    return ChatResult(runtime="fake", model="m", text=text, tool_calls=calls or [], latency_ms=10.0)


def tool_case(tool: str | None, args: dict | None = None) -> GoldenCase:
    return GoldenCase(
        id="c",
        task="tool_call",
        messages=[Message(role="user", content="x")],
        tools=[WEATHER, CALC],
        expected={"tool": tool, "arguments": args or {}},
    )


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {"total_price": {"type": ["string", "null"]}},
    "required": ["total_price"],
}


def extraction_case() -> GoldenCase:
    return GoldenCase(
        id="e",
        task="extraction",
        messages=[Message(role="user", content="x")],
        response_schema=EXTRACTION_SCHEMA,
        expected={"total_price": "45,500"},
    )


def test_extraction_pass_normalizes_amounts():
    outcome = score_extraction(extraction_case(), result('{"total_price": "45500"}'))
    assert outcome.passed


def test_extraction_invalid_json_is_classified():
    outcome = score_extraction(extraction_case(), result("Sure! {total_price: 1}"))
    assert outcome.failure == "invalid_json"


def test_extraction_fenced_json_is_not_silently_accepted():
    outcome = score_extraction(extraction_case(), result('```json\n{"total_price": "1"}\n```'))
    assert outcome.failure == "invalid_json"


def test_extraction_schema_violation():
    outcome = score_extraction(extraction_case(), result('{"other": 1}'))
    assert outcome.failure == "schema_invalid"


def test_extraction_wrong_value_reports_fields():
    outcome = score_extraction(extraction_case(), result('{"total_price": "99,000"}'))
    assert outcome.failure == "wrong_value"
    assert outcome.detail["fields"] == {"total_price": False}


def test_tool_call_pass():
    case = tool_case("get_weather", {"city": "Istanbul"})
    out = score_tool_call(
        case, result(calls=[ToolCall(name="get_weather", arguments={"city": "istanbul"})])
    )
    assert out.passed


def test_tool_call_no_call():
    out = score_tool_call(tool_case("get_weather", {"city": "X"}), result("It is sunny."))
    assert out.failure == "no_call"


def test_tool_call_unexpected_call():
    out = score_tool_call(
        tool_case(None), result(calls=[ToolCall(name="get_weather", arguments={"city": "X"})])
    )
    assert out.failure == "unexpected_call"


def test_tool_call_correct_abstention():
    assert score_tool_call(tool_case(None), result("Hello!")).passed


def test_tool_call_hallucinated_tool():
    out = score_tool_call(
        tool_case("get_weather", {"city": "X"}),
        result(calls=[ToolCall(name="send_email", arguments={})]),
    )
    assert out.failure == "hallucinated_tool"


def test_tool_call_wrong_tool():
    out = score_tool_call(
        tool_case("get_weather", {"city": "X"}),
        result(calls=[ToolCall(name="calculator", arguments={"expression": "1+1"})]),
    )
    assert out.failure == "wrong_tool"


def test_tool_call_bad_args_schema():
    out = score_tool_call(
        tool_case("get_weather", {"city": "X"}),
        result(calls=[ToolCall(name="get_weather", arguments={"town": "X"})]),
    )
    assert out.failure == "bad_args_schema"


def test_tool_call_wrong_args():
    out = score_tool_call(
        tool_case("get_weather", {"city": "Ankara"}),
        result(calls=[ToolCall(name="get_weather", arguments={"city": "Izmir"})]),
    )
    assert out.failure == "wrong_args"


def test_extraction_truncation_is_its_own_category():
    truncated = ChatResult(
        runtime="fake", model="m", text="", latency_ms=1.0, finish_reason="length"
    )
    assert score_extraction(extraction_case(), truncated).failure == "truncated"


def test_tool_call_truncation_is_its_own_category():
    truncated = ChatResult(
        runtime="fake", model="m", text="", latency_ms=1.0, finish_reason="length"
    )
    assert (
        score_tool_call(tool_case("get_weather", {"city": "X"}), truncated).failure == "truncated"
    )


def test_tool_call_ignores_diacritics_in_string_args():
    out = score_tool_call(
        tool_case("get_weather", {"city": "Istanbul"}),
        result(calls=[ToolCall(name="get_weather", arguments={"city": "\u0130stanbul"})]),
    )
    assert out.passed


MULTI_SCHEMA = {
    "type": "object",
    "properties": {
        "receipts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"total_price": {"type": ["string", "null"]}},
                "required": ["total_price"],
            },
        }
    },
    "required": ["receipts"],
}


def multi_case() -> GoldenCase:
    return GoldenCase(
        id="m",
        task="multi_extraction",
        messages=[Message(role="user", content="x")],
        response_schema=MULTI_SCHEMA,
        expected={"totals": ["10,000", "20,000", "30,000"]},
    )


def multi_output(*totals: str) -> str:
    import json

    return json.dumps({"receipts": [{"total_price": t} for t in totals]})


def test_multi_extraction_pass():
    from controlplane.evals.scorers import score_multi_extraction

    out = score_multi_extraction(multi_case(), result(multi_output("10000", "20.000", "30,000")))
    assert out.passed and out.detail["item_accuracy"] == 1.0


def test_multi_extraction_count_mismatch_keeps_partial_credit():
    from controlplane.evals.scorers import score_multi_extraction

    out = score_multi_extraction(multi_case(), result(multi_output("10,000", "20,000")))
    assert out.failure == "count_mismatch"
    assert out.detail["actual_count"] == 2 and out.detail["expected_count"] == 3


def test_multi_extraction_wrong_value_partial_credit():
    from controlplane.evals.scorers import score_multi_extraction

    out = score_multi_extraction(multi_case(), result(multi_output("10,000", "99,000", "30,000")))
    assert out.failure == "wrong_value"
    assert abs(out.detail["item_accuracy"] - 2 / 3) < 1e-9


def test_every_golden_file_has_a_cli_suite_and_loads():
    from pathlib import Path

    from controlplane.cli import SUITES
    from controlplane.evals.contract import load_cases

    on_disk = {p.stem for p in Path("golden").glob("*.jsonl")}
    assert on_disk == set(SUITES)
    for path in SUITES.values():
        assert load_cases(path)
