import time

import httpx

from controlplane.types import ChatRequest, ChatResult, Message, RuntimeError_, ToolCall, Usage


def _message(message: Message) -> dict:
    out: dict = {"role": message.role, "content": message.content}
    if message.tool_calls:
        out["tool_calls"] = [
            {"function": {"name": c.name, "arguments": c.arguments}} for c in message.tool_calls
        ]
    if message.role == "tool" and message.tool_name:
        out["tool_name"] = message.tool_name
    return out


def _with_no_think(messages: list[dict]) -> list[dict]:
    out = [dict(m) for m in messages]
    for message in out:
        if message["role"] == "system":
            message["content"] = f"{message['content']}\n/no_think"
            return out
    return [{"role": "system", "content": "/no_think"}, *out]


class OllamaClient:
    """`soft_no_think=True` turns reasoning off the way Qwen3 documents it, with a "/no_think"
    switch in the system prompt, instead of the API's `think` flag (which leaks reasoning into the
    content for qwen3:30b-a3b). It is reported as the separate runtime "ollama-nothink"."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_s: float = 300.0,
        transport: httpx.BaseTransport | None = None,
        soft_no_think: bool = False,
    ):
        self.soft_no_think = soft_no_think
        self.runtime = "ollama-nothink" if soft_no_think else "ollama"
        self._http = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)

    def chat(self, request: ChatRequest) -> ChatResult:
        messages = [_message(m) for m in request.messages]
        if self.soft_no_think and request.think is False:
            messages = _with_no_think(messages)
        body: dict = {
            "model": request.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "seed": request.seed,
                "num_predict": request.max_tokens,
            },
        }
        if request.think is not None and not self.soft_no_think:
            body["think"] = request.think
        if request.response_schema is not None:
            body["format"] = request.response_schema
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in request.tools
            ]

        started = time.perf_counter()
        try:
            response = self._http.post("/api/chat", json=body)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError_(f"ollama request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000
        data = response.json()

        message = data.get("message", {})
        tool_calls = [
            ToolCall(
                name=call["function"]["name"],
                arguments=call["function"].get("arguments") or {},
            )
            for call in message.get("tool_calls") or []
        ]
        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration") or 0
        return ChatResult(
            runtime=self.runtime,
            model=request.model,
            text=message.get("content", ""),
            tool_calls=tool_calls,
            usage=Usage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=eval_count,
            ),
            latency_ms=latency_ms,
            schema_enforced=request.response_schema is not None,
            finish_reason=data.get("done_reason"),
            generation_tps=(eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns else None,
        )
