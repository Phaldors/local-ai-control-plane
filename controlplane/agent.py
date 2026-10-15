"""Tool-use loop: model -> tool calls -> results fed back -> model, until a plain answer.

Bad model behaviour never aborts the loop: unknown tools and invalid arguments come back as
tool errors (the model may recover), and are recorded as flags for the scorer.
"""

import json
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field

from controlplane.client import LLMClient
from controlplane.types import ChatRequest, Message, ToolCall
from controlplane.worlds.shop import ShopWorld


class Step(BaseModel):
    tool: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    flags: list[str] = Field(default_factory=list)


class AgentRun(BaseModel):
    steps: list[Step] = Field(default_factory=list)
    final_text: str = ""
    # "answered" = model stopped calling tools, "step_limit", or "length" (token cap hit)
    ended: str = "answered"
    model_turns: int = 0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    refunds: list[dict[str, Any]] = Field(default_factory=list)
    tickets: list[dict[str, Any]] = Field(default_factory=list)


def run_agent(
    client: LLMClient,
    model: str,
    messages: list[Message],
    world: ShopWorld,
    max_turns: int = 10,
    max_tokens: int = 1024,
    think: bool | None = None,
) -> AgentRun:
    run = AgentRun()
    specs = {s.name: s for s in world.specs}
    history = list(messages)
    call_counter = 0

    for _ in range(max_turns):
        result = client.chat(
            ChatRequest(
                model=model, messages=history, tools=world.specs, max_tokens=max_tokens, think=think
            )
        )
        run.model_turns += 1
        run.latency_ms += result.latency_ms
        run.prompt_tokens += result.usage.prompt_tokens
        run.completion_tokens += result.usage.completion_tokens

        if not result.tool_calls:
            run.final_text = result.text
            run.ended = (
                "length" if result.finish_reason == "length" and not result.text else "answered"
            )
            break

        calls = []
        for call in result.tool_calls:
            call_counter += 1
            calls.append(
                ToolCall(name=call.name, arguments=call.arguments, id=f"call_{call_counter}")
            )
        history.append(Message(role="assistant", content=result.text, tool_calls=calls))

        for call in calls:
            flags: list[str] = []
            spec = specs.get(call.name)
            if spec is None:
                flags.append("hallucinated_tool")
                output: dict[str, Any] = {"error": "unknown_tool"}
            elif list(Draft202012Validator(spec.parameters).iter_errors(call.arguments)):
                flags.append("bad_args_schema")
                output = {"error": "invalid_arguments"}
            else:
                output = world.execute(call)
                if "error" in output:
                    flags.append("tool_error")
            run.steps.append(
                Step(tool=call.name, arguments=call.arguments, result=output, flags=flags)
            )
            history.append(
                Message(
                    role="tool",
                    content=json.dumps(output),
                    tool_name=call.name,
                    tool_call_id=call.id,
                )
            )
    else:
        run.ended = "step_limit"

    run.refunds = world.refunds
    run.tickets = world.tickets
    return run
