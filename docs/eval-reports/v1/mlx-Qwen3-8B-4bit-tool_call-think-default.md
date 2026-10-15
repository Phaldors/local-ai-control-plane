# Eval run 20261015T165321Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `tool_call` (25 cases, split `validation`)
- max_tokens: 1024, think: None
- commit: `4fe530a`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **24/25 (96%)**
- latency p50/p95: 3465 ms / 5975 ms
- completion tokens (mean): 186

### Failures (reported, never hidden)

- `wrong_args`: 1 (tool-c2)
