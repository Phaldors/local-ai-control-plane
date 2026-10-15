# Eval run 20261015T175437Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: None
- resident model memory (approx): 1.4 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **34/50 (68%)**
- latency p50/p95: 8811 ms / 10933 ms
- completion tokens (mean): 849
- JSON valid: 70%, schema valid: 70%
- field accuracy: {'total_price': 0.9714285714285714, 'subtotal_price': 0.9642857142857143, 'item_count': 1.0}

### Failures (reported, never hidden)

- `truncated`: 15 (cord-val-004, cord-val-005, cord-val-007, cord-val-010, cord-val-012, cord-val-015, cord-val-018, cord-val-021, cord-val-022, cord-val-026)
- `wrong_value`: 1 (cord-val-044)
