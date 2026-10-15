# Eval run 20261015T163820Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: False
- commit: `2225240`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **44/50 (88%)**
- latency p50/p95: 563 ms / 651 ms
- completion tokens (mean): 40
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.96, 'item_count': 0.92}

### Failures (reported, never hidden)

- `wrong_value`: 6 (cord-val-004, cord-val-021, cord-val-022, cord-val-036, cord-val-041, cord-val-047)
