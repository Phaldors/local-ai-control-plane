# Eval run 20261015T193614Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `tool_call` (20 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 4.6 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **18/20 (90%)**
- latency p50/p95: 690 ms / 1092 ms
- completion tokens (mean): 48

### Failures (reported, never hidden)

- `no_call`: 2 (tool-test-o2, tool-test-o3)
