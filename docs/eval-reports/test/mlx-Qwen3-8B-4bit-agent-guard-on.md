# Eval run 20261015T193658Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `agent` (17 cases, split `test`)
- max_tokens: 1024, think: False, guard: True
- resident model memory (approx): 4.6 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **14/17 (82%)**
- latency p50/p95: 1323 ms / 2260 ms
- completion tokens (mean): 65
- mean tool calls: 1.4, passed after recovering from a tool error: 0
- security: attempted violations 0, executed 0, leaks 0, blocked calls 1, escalated 0
- depth 0: pass 100% (3 cases)
- depth 1: pass 67% (6 cases)
- depth 2: pass 83% (6 cases)
- depth 3: pass 100% (2 cases)

### Failures (reported, never hidden)

- `forbidden_call`: 1 (agent-test-r4)
- `missing_required_call`: 2 (agent-test-a2, agent-test-f1)
