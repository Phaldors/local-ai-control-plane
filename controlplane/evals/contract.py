"""Golden eval contract.

A case is data, a scorer is deterministic code. Failures are first-class output:
every case that does not pass is classified and reported, never dropped.
"""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from controlplane.types import Message, ToolSpec


class GoldenCase(BaseModel):
    id: str
    task: Literal["extraction", "tool_call", "multi_extraction"]
    split: Literal["validation", "test"] = "validation"
    messages: list[Message]
    response_schema: dict[str, Any] | None = None
    tools: list[ToolSpec] = Field(default_factory=list)
    # extraction: {"field": expected_value_or_null}
    # tool_call:  {"tool": name_or_null, "arguments": {...}}
    expected: dict[str, Any]
    tags: list[str] = Field(default_factory=list)


class CaseOutcome(BaseModel):
    case_id: str
    task: str
    passed: bool
    # Empty when passed. One of the failure categories below.
    failure: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


EXTRACTION_FAILURES = (
    "transport_error",
    "truncated",
    "invalid_json",
    "schema_invalid",
    "wrong_value",
)
MULTI_EXTRACTION_FAILURES = (
    "transport_error",
    "truncated",
    "invalid_json",
    "schema_invalid",
    "count_mismatch",
    "wrong_value",
)
TOOL_CALL_FAILURES = (
    "transport_error",
    "truncated",
    "no_call",
    "unexpected_call",
    "hallucinated_tool",
    "wrong_tool",
    "bad_args_schema",
    "wrong_args",
)


def load_cases(path: Path, split: str | None = None) -> list[GoldenCase]:
    cases = [
        GoldenCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [c for c in cases if split is None or c.split == split]


def dump_cases(cases: list[GoldenCase], path: Path) -> None:
    path.write_text(
        "\n".join(json.dumps(c.model_dump(), ensure_ascii=False) for c in cases) + "\n",
        encoding="utf-8",
    )
