"""Detect reasoning that leaked into the visible answer although thinking was requested off.

Observed case: Ollama with `think=false` on qwen3:30b-a3b returns "Okay, let's see. The user wants
a refund..." as plain content. A leak makes a "thinking off" run slower and costlier than its label,
and the flag is not portable across runtimes, so it is measured from the output, not trusted.

The detector is deliberately narrow: a reasoning opener at the very start of the text followed,
within a short window, by first-person planning language. It will miss other styles; it should not
flag normal answers such as "Okay, the order is pending."
"""

import re

_OPENER = r"(?:okay|ok|alright|hmm+|so|well|let me think|first)"
_PLANNING = r"(?:the user|let me|let's|i need|i should|i'll|i will need|i have to|wait)"
_LEAK = re.compile(
    rf"^\s*{_OPENER}\b[,.:!\s]{{0,4}}.{{0,60}}?\b{_PLANNING}\b", re.IGNORECASE | re.DOTALL
)


def looks_like_leaked_reasoning(text: str) -> bool:
    return bool(text) and _LEAK.match(text[:200]) is not None
