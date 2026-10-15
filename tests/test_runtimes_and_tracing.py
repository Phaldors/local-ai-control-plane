import json

import httpx
import pytest

from controlplane.evals.contract import GoldenCase
from controlplane.evals.runner import run_eval
from controlplane.runtimes.mlx import MLXClient
from controlplane.runtimes.ollama import OllamaClient
from controlplane.tracing import TracedClient, TraceSink
from controlplane.types import ChatRequest, ChatResult, Message, RuntimeError_, ToolSpec

TOOL = ToolSpec(
    name="get_weather",
    description="weather",
    parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
)


def request(**kw) -> ChatRequest:
    return ChatRequest(model="m", messages=[Message(role="user", content="hi")], **kw)


def test_ollama_parses_tool_calls_usage_and_tps():
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        assert body["tools"][0]["function"]["name"] == "get_weather"
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "get_weather", "arguments": {"city": "Rome"}}}
                    ],
                },
                "prompt_eval_count": 12,
                "eval_count": 20,
                "eval_duration": 1_000_000_000,
            },
        )

    client = OllamaClient(transport=httpx.MockTransport(handler))
    out = client.chat(request(tools=[TOOL]))
    assert out.tool_calls[0].arguments == {"city": "Rome"}
    assert out.usage.prompt_tokens == 12
    assert out.generation_tps == 20.0


def test_ollama_sends_think_flag_and_reports_finish_reason():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"message": {"content": ""}, "done_reason": "length"})

    out = OllamaClient(transport=httpx.MockTransport(handler)).chat(request(think=False))
    assert seen["body"]["think"] is False
    assert out.finish_reason == "length"


def test_ollama_marks_schema_enforced_only_when_schema_sent():
    handler = lambda r: httpx.Response(200, json={"message": {"content": "{}"}})  # noqa: E731
    client = OllamaClient(transport=httpx.MockTransport(handler))
    assert client.chat(request(response_schema={"type": "object"})).schema_enforced is True
    assert client.chat(request()).schema_enforced is False


def test_mlx_never_claims_schema_enforcement_and_injects_instruction():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(req.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )

    client = MLXClient(transport=httpx.MockTransport(handler))
    out = client.chat(request(response_schema={"type": "object"}))
    assert out.schema_enforced is False
    assert seen["body"]["messages"][0]["role"] == "system"


def test_mlx_parses_string_tool_arguments():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city": "Rome"}',
                                    }
                                }
                            ],
                        }
                    }
                ]
            },
        )

    out = MLXClient(transport=httpx.MockTransport(handler)).chat(request(tools=[TOOL]))
    assert out.tool_calls[0].arguments == {"city": "Rome"}


def test_transport_failure_raises_runtime_error():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(RuntimeError_):
        OllamaClient(transport=httpx.MockTransport(handler)).chat(request())


class FakeClient:
    runtime = "fake"

    def __init__(self, text: str = '{"total_price": "45500"}', fail: bool = False):
        self.text = text
        self.fail = fail

    def chat(self, req: ChatRequest) -> ChatResult:
        if self.fail:
            raise RuntimeError_("down")
        return ChatResult(runtime="fake", model=req.model, text=self.text, latency_ms=5.0)


def test_traced_client_records_success_and_failure(tmp_path):
    sink = TraceSink(tmp_path / "t.jsonl")
    TracedClient(FakeClient(), sink, "run1").chat(request())
    with pytest.raises(RuntimeError_):
        TracedClient(FakeClient(fail=True), sink, "run1").chat(request())
    lines = [json.loads(line) for line in sink.path.read_text().splitlines()]
    assert [line["status"] for line in lines] == ["ok", "transport_error"]


def extraction_case() -> GoldenCase:
    return GoldenCase(
        id="e1",
        task="extraction",
        messages=[Message(role="user", content="x")],
        response_schema={
            "type": "object",
            "properties": {"total_price": {"type": ["string", "null"]}},
            "required": ["total_price"],
        },
        expected={"total_price": "45,500"},
    )


def test_run_eval_writes_report_with_failures_visible(tmp_path):
    run_dir = run_eval(
        FakeClient(text="not json"), "m", [extraction_case()], "extraction", "validation", tmp_path
    )
    report = json.loads((run_dir / "report.json").read_text())
    failures = report["tasks"]["extraction"]["failures"]
    assert failures["invalid_json"]["case_ids"] == ["e1"]
    assert "invalid_json" in (run_dir / "report.md").read_text()
    assert (run_dir / "traces.jsonl").exists()


def test_run_eval_counts_transport_errors_as_failures_not_crashes(tmp_path):
    run_dir = run_eval(
        FakeClient(fail=True), "m", [extraction_case()], "extraction", "validation", tmp_path
    )
    report = json.loads((run_dir / "report.json").read_text())
    assert report["tasks"]["extraction"]["failures"]["transport_error"]["count"] == 1
