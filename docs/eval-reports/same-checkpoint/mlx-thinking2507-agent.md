# Eval run 20261015T204425Z-mlx-mlx-community_Qwen3-30B-A3B-Thinking-2507-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-Thinking-2507-4bit`
- suite: `agent` (29 cases, split `validation`)
- max_tokens: 4096, think: None, guard: off
- resident model memory (approx): 16.3 GB
- reasoning leak: n/a (thinking not requested off)
- commit: `058fb5b`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **28/29 (97%)**
- latency p50/p95: 7423 ms / 29388 ms
- completion tokens (mean): 886
- mean tool calls: 1.8, passed after recovering from a tool error: 1
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
