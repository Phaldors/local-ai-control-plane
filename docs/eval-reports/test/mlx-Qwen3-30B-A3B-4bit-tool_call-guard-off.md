# Eval run 20261015T193234Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `tool_call` (20 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 16.3 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **19/20 (95%)**
- latency p50/p95: 411 ms / 577 ms
- completion tokens (mean): 37

### Failures (reported, never hidden)

- `no_call`: 1 (tool-test-w3)
