# Eval run 20261015T204251Z-mlx-mlx-community_Qwen3-30B-A3B-Thinking-2507-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-Thinking-2507-4bit`
- suite: `tool_call` (37 cases, split `validation`)
- max_tokens: 4096, think: None, guard: off
- resident model memory (approx): 16.3 GB
- reasoning leak: n/a (thinking not requested off)
- commit: `058fb5b`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **35/37 (95%)**
- latency p50/p95: 2303 ms / 3781 ms
- completion tokens (mean): 220

### Failures (reported, never hidden)

- `unexpected_call`: 1 (tool-h1)
- `wrong_args`: 1 (tool-t1)
