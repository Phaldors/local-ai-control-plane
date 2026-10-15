from typing import Protocol

from controlplane.types import ChatRequest, ChatResult


class LLMClient(Protocol):
    """The only surface the eval and (later) the router talk to."""

    runtime: str

    def chat(self, request: ChatRequest) -> ChatResult: ...
