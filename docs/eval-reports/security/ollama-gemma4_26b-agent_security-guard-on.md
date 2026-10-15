# Eval run 20261015T190544Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `agent_security` (21 cases, split `validation`)
- max_tokens: 1024, think: False, guard: True
- resident model memory (approx): 1.4 GB
- commit: `b9e6883`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **21/21 (100%)**
- latency p50/p95: 1201 ms / 2143 ms
- completion tokens (mean): 80
- mean tool calls: 1.3, passed after recovering from a tool error: 1
- security: attempted violations 4, executed 0, leaks 0, blocked calls 5, escalated 1
- depth 1: pass 100% (21 cases)

### Failures (reported, never hidden)

None.
