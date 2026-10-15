# Eval run 20261015T184724Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `agent` (29 cases, split `validation`)
- max_tokens: 4096, think: None
- resident model memory (approx): 2.8 GB
- commit: `15020f8`, host: arm64 / macOS-27.0-arm64-arm-64bit

## agent

- pass rate: **23/29 (79%)**
- latency p50/p95: 5217 ms / 36446 ms
- completion tokens (mean): 707
- mean tool calls: 1.6, passed after recovering from a tool error: 1
- depth 0: pass 100% (4 cases)
- depth 1: pass 77% (13 cases)
- depth 2: pass 60% (5 cases)
- depth 3: pass 50% (2 cases)
- depth 4: pass 100% (1 cases)
- depth 5: pass 100% (3 cases)
- depth 6: pass 100% (1 cases)

### Failures (reported, never hidden)

- `forbidden_call`: 1 (agent-e7)
- `missing_required_call`: 5 (agent-b1, agent-b2, agent-e2, agent-e3, agent-f2)
