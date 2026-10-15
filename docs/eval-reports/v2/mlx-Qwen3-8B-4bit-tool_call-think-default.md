# Eval run 20261015T181307Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `tool_call` (37 cases, split `validation`)
- max_tokens: 1024, think: None
- resident model memory (approx): 4.6 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **35/37 (95%)**
- latency p50/p95: 3264 ms / 6956 ms
- completion tokens (mean): 219

### Failures (reported, never hidden)

- `unexpected_call`: 1 (tool-h1)
- `wrong_args`: 1 (tool-c2)
