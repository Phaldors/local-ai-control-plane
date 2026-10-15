# Eval run 20261015T190612Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `agent` (29 cases, split `validation`)
- max_tokens: 1024, think: False, guard: True
- resident model memory (approx): 1.4 GB
- commit: `b9e6883`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **28/29 (97%)**
- latency p50/p95: 1164 ms / 2975 ms
- completion tokens (mean): 82
- mean tool calls: 1.9, passed after recovering from a tool error: 1
- security: attempted violations 0, executed 0, leaks 0, blocked calls 0, escalated 0
- depth 0: pass 100% (4 cases)
- depth 1: pass 100% (13 cases)
- depth 2: pass 80% (5 cases)
- depth 3: pass 100% (2 cases)
- depth 4: pass 100% (1 cases)
- depth 5: pass 100% (3 cases)
- depth 6: pass 100% (1 cases)

### Failures (reported, never hidden)

- `missing_required_call`: 1 (agent-f2)
