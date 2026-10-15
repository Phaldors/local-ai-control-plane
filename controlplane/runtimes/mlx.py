"""MLX-LM runtime via its OpenAI-compatible server (`mlx_lm.server`).

mlx_lm.server does not do grammar-constrained decoding, so a response schema is
only *requested* in the prompt. `schema_enforced` stays False and the eval
measures how often the model actually complies.
"""

import json
import time

import httpx

from controlplane.types import ChatRequest, ChatResult, RuntimeError_, ToolCall, Usage


class MLXClient:
    runtime = "mlx"

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout_s: float = 300.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._http = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)

    def chat(self, request: ChatRequest) -> ChatResult:
        messages = [m.model_dump() for m in request.messages]
        if request.response_schema is not None:
            instruction = (
                "Respond with a single JSON object that matches this JSON schema. "
                "No prose, no code fences.\n" + json.dumps(request.response_schema)
            )
            messages.insert(0, {"role": "system", "content": instruction})

        body: dict = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "seed": request.seed,
            "stream": False,
        }
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
            response = self._http.post("/v1/chat/completions", json=body)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError_(f"mlx request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000
        data = response.json()

        message = data["choices"][0]["message"]
        tool_calls = []
        for call in message.get("tool_calls") or []:
            arguments = call["function"].get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"__unparsed__": arguments}
            tool_calls.append(ToolCall(name=call["function"]["name"], arguments=arguments))

        usage = data.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        return ChatResult(
            runtime=self.runtime,
            model=request.model,
            text=message.get("content") or "",
            tool_calls=tool_calls,
            usage=Usage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=completion_tokens,
            ),
            latency_ms=latency_ms,
            schema_enforced=False,
            finish_reason=data["choices"][0].get("finish_reason"),
            generation_tps=(completion_tokens / (latency_ms / 1000)) if latency_ms else None,
        )
