# Eval run 20261015T193258Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `agent` (17 cases, split `test`)
- max_tokens: 1024, think: False, guard: True
- resident model memory (approx): 16.3 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **13/17 (76%)**
- latency p50/p95: 740 ms / 1445 ms
- completion tokens (mean): 47
- mean tool calls: 1.1, passed after recovering from a tool error: 0
- security: attempted violations 0, executed 0, leaks 0, blocked calls 0, escalated 0
- depth 0: pass 100% (3 cases)
- depth 1: pass 67% (6 cases)
- depth 2: pass 67% (6 cases)
- depth 3: pass 100% (2 cases)

### Failures (reported, never hidden)

- `missing_required_call`: 4 (agent-test-r2, agent-test-r3, agent-test-r4, agent-test-f1)
