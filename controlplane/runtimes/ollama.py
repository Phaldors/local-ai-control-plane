import time

import httpx

from controlplane.types import ChatRequest, ChatResult, RuntimeError_, ToolCall, Usage


class OllamaClient:
    runtime = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_s: float = 300.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._http = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)

    def chat(self, request: ChatRequest) -> ChatResult:
        body: dict = {
            "model": request.model,
            "messages": [m.model_dump() for m in request.messages],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "seed": request.seed,
                "num_predict": request.max_tokens,
            },
        }
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
            generation_tps=(eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns else None,
        )
