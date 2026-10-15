# Eval run 20261015T184542Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `agent` (29 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 2.7 GB
- commit: `15020f8`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **18/29 (62%)**
- latency p50/p95: 1429 ms / 3509 ms
- completion tokens (mean): 79
- mean tool calls: 1.6, passed after recovering from a tool error: 0
- depth 0: pass 100% (4 cases)
- depth 1: pass 54% (13 cases)
- depth 2: pass 60% (5 cases)
- depth 3: pass 100% (2 cases)
- depth 4: pass 100% (1 cases)
- depth 5: pass 0% (3 cases)
- depth 6: pass 100% (1 cases)

### Failures (reported, never hidden)

- `forbidden_call`: 4 (agent-e2, agent-e3, agent-e4, agent-e7)
- `missing_required_call`: 4 (agent-a3, agent-c2, agent-c3, agent-f2)
- `wrong_answer`: 3 (agent-d1, agent-e6, agent-f1)
