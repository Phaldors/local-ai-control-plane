# Eval run 20261015T200333Z-ollama-qwen3_30b-a3b

- runtime: `ollama`, model: `qwen3:30b-a3b`
- suite: `tool_call` (37 cases, split `validation`)
- max_tokens: 1024, think: False, guard: off
- resident model memory (approx): 21.3 GB
- commit: `d27159f`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **35/37 (95%)**
- latency p50/p95: 2131 ms / 4296 ms
- completion tokens (mean): 245

### Failures (reported, never hidden)

- `unexpected_call`: 1 (tool-h1)
- `wrong_args`: 1 (tool-t1)
