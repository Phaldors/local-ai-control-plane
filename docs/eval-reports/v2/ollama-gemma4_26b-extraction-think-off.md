# Eval run 20261015T175319Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 1.4 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **49/50 (98%)**
- latency p50/p95: 551 ms / 648 ms
- completion tokens (mean): 40
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 1.0, 'item_count': 0.9642857142857143}

### Failures (reported, never hidden)

- `wrong_value`: 1 (cord-val-041)
