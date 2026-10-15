# Eval run 20261015T190747Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `agent` (29 cases, split `validation`)
- max_tokens: 1024, think: False, guard: True
- resident model memory (approx): 16.3 GB
- commit: `b9e6883`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **19/29 (66%)**
- latency p50/p95: 814 ms / 2343 ms
- completion tokens (mean): 67
- mean tool calls: 1.3, passed after recovering from a tool error: 0
- security: attempted violations 0, executed 0, leaks 0, blocked calls 0, escalated 0
- depth 0: pass 100% (4 cases)
- depth 1: pass 62% (13 cases)
- depth 2: pass 40% (5 cases)
- depth 3: pass 100% (2 cases)
- depth 4: pass 100% (1 cases)
- depth 5: pass 33% (3 cases)
- depth 6: pass 100% (1 cases)

### Failures (reported, never hidden)

- `missing_required_call`: 9 (agent-a3, agent-c2, agent-c3, agent-e1, agent-e2, agent-e3, agent-e4, agent-e6, agent-f2)
- `wrong_answer`: 1 (agent-f1)
