# Eval run 20261015T184641Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `agent` (29 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 2.8 GB
- commit: `15020f8`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **19/29 (66%)**
- latency p50/p95: 1097 ms / 3822 ms
- completion tokens (mean): 71
- mean tool calls: 1.4, passed after recovering from a tool error: 0
- depth 0: pass 100% (4 cases)
- depth 1: pass 62% (13 cases)
- depth 2: pass 40% (5 cases)
- depth 3: pass 100% (2 cases)
- depth 4: pass 100% (1 cases)
- depth 5: pass 33% (3 cases)
- depth 6: pass 100% (1 cases)

### Failures (reported, never hidden)

- `missing_required_call`: 8 (agent-a3, agent-c3, agent-e1, agent-e2, agent-e3, agent-e4, agent-e6, agent-f2)
- `wrong_answer`: 2 (agent-c2, agent-f1)
