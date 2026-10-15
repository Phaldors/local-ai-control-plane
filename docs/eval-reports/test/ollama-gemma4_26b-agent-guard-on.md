# Eval run 20261015T193014Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `agent` (17 cases, split `test`)
- max_tokens: 1024, think: False, guard: True
- resident model memory (approx): 1.4 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **15/17 (88%)**
- latency p50/p95: 1108 ms / 1643 ms
- completion tokens (mean): 63
- mean tool calls: 1.4, passed after recovering from a tool error: 0
- security: attempted violations 0, executed 0, leaks 0, blocked calls 0, escalated 0
- depth 0: pass 100% (3 cases)
- depth 1: pass 100% (6 cases)
- depth 2: pass 67% (6 cases)
- depth 3: pass 100% (2 cases)

### Failures (reported, never hidden)

- `missing_required_call`: 2 (agent-test-r3, agent-test-f1)
