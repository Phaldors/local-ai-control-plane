# Eval run 20261015T200210Z-ollama-qwen3_30b-a3b

- runtime: `ollama`, model: `qwen3:30b-a3b`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: False, guard: off
- resident model memory (approx): 21.3 GB
- commit: `d27159f`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **47/50 (94%)**
- latency p50/p95: 454 ms / 541 ms
- completion tokens (mean): 34
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.9523809523809523, 'item_count': 0.9642857142857143}

### Failures (reported, never hidden)

- `wrong_value`: 3 (cord-val-005, cord-val-021, cord-val-041)
