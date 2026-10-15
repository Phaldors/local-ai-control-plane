# Eval run 20261015T180336Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `tool_call` (37 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 4.6 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **32/37 (86%)**
- latency p50/p95: 616 ms / 1253 ms
- completion tokens (mean): 40

### Failures (reported, never hidden)

- `no_call`: 4 (tool-o1, tool-o4, tool-m3, tool-h11)
- `unexpected_call`: 1 (tool-h1)
