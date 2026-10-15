# Eval run 20261015T164301Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `tool_call` (25 cases, split `validation`)
- max_tokens: 1024, think: False
- commit: `4fe530a`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **22/25 (88%)**
- latency p50/p95: 699 ms / 1449 ms
- completion tokens (mean): 33

### Failures (reported, never hidden)

- `no_call`: 3 (tool-o1, tool-o4, tool-m3)
