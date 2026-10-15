from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    response_schema: dict[str, Any] | None = None
    tools: list[ToolSpec] = Field(default_factory=list)
    max_tokens: int = 1024
    temperature: float = 0.0
    seed: int = 0


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ChatResult(BaseModel):
    runtime: str
    model: str
    text: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    latency_ms: float
    # True only when the runtime itself guarantees schema-shaped output
    # (grammar-constrained decoding). False means validity is best-effort and
    # must be measured, never assumed.
    schema_enforced: bool = False
    # Runtime-reported generation speed when available; None means unknown.
    generation_tps: float | None = None


class RuntimeError_(Exception):
    """Transport or server failure. Model misbehaviour is never raised, it is
    returned in ChatResult and scored by the eval."""
