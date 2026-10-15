# Eval run 20261015T182150Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `tool_call` (37 cases, split `validation`)
- max_tokens: 1024, think: None
- resident model memory (approx): 16.3 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **34/37 (92%)**
- latency p50/p95: 1904 ms / 4243 ms
- completion tokens (mean): 202

### Failures (reported, never hidden)

- `unexpected_call`: 1 (tool-h1)
- `wrong_args`: 2 (tool-t1, tool-c2)
