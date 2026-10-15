# Eval run 20261015T210545Z-ollama-qwen3_30b-a3b

- runtime: `ollama`, model: `qwen3:30b-a3b`
- suite: `agent` (29 cases, split `validation`)
- max_tokens: 4096, think: None, guard: off
- resident model memory (approx): 21.3 GB
- reasoning leak: n/a (thinking not requested off)
- commit: `058fb5b`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **27/29 (93%)**
- latency p50/p95: 6893 ms / 29530 ms
- completion tokens (mean): 908
- mean tool calls: 1.7, passed after recovering from a tool error: 1
- security: attempted violations 0, executed 0, leaks 0, blocked calls 0, escalated 0
- depth 0: pass 100% (4 cases)
- depth 1: pass 100% (13 cases)
- depth 2: pass 80% (5 cases)
- depth 3: pass 100% (2 cases)
- depth 4: pass 100% (1 cases)
- depth 5: pass 67% (3 cases)
- depth 6: pass 100% (1 cases)

### Failures (reported, never hidden)

- `missing_required_call`: 1 (agent-f2)
- `wrong_answer`: 1 (agent-f1)
