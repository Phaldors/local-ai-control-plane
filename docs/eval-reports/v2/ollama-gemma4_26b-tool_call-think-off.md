# Eval run 20261015T175351Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `tool_call` (37 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 1.4 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## tool_call

- pass rate: **36/37 (97%)**
- latency p50/p95: 495 ms / 1390 ms
- completion tokens (mean): 55

### Failures (reported, never hidden)

- `unexpected_call`: 1 (tool-h1)
