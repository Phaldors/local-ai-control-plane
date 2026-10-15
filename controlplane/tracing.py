import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from controlplane.client import LLMClient
from controlplane.redaction import redact_obj
from controlplane.types import ChatRequest, ChatResult


class TraceSink:
    """Append-only JSONL, one line per LLM call, successful or not."""

    def __init__(self, path: Path, redact: bool = True):
        self.path = path
        self.redact = redact
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict) -> None:
        if self.redact:
            record = redact_obj(record)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _request_hash(request: ChatRequest) -> str:
    payload = request.model_dump_json(exclude={"max_tokens"})
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class TracedClient:
    """Wraps any LLMClient; every call leaves a trace, even when it raises."""

    def __init__(self, inner: LLMClient, sink: TraceSink, run_id: str, tag: str | None = None):
        self._inner = inner
        self._sink = sink
        self._run_id = run_id
        self._tag = tag
        self.runtime = inner.runtime

    def chat(self, request: ChatRequest) -> ChatResult:
        base = {
            "trace_id": uuid.uuid4().hex,
            "run_id": self._run_id,
            "tag": self._tag,
            "ts": datetime.now(UTC).isoformat(),
            "runtime": self._inner.runtime,
            "model": request.model,
            "request_hash": _request_hash(request),
            "temperature": request.temperature,
            "seed": request.seed,
            "messages": [m.model_dump() for m in request.messages],
        }
        started = time.perf_counter()
        try:
            result = self._inner.chat(request)
        except Exception as exc:
            self._sink.write(
                {
                    **base,
                    "status": "transport_error",
                    "error": repr(exc),
                    "latency_ms": (time.perf_counter() - started) * 1000,
                }
            )
            raise
        self._sink.write(
            {
                **base,
                "status": "ok",
                "latency_ms": result.latency_ms,
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "generation_tps": result.generation_tps,
                "schema_enforced": result.schema_enforced,
                "output": result.text,
                "tool_calls": [c.model_dump() for c in result.tool_calls],
            }
        )
        return result
