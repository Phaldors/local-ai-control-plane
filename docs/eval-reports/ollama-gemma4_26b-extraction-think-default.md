# Eval run 20261015T163019Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: None
- commit: `2225240`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **33/50 (66%)**
- latency p50/p95: 8967 ms / 11394 ms
- completion tokens (mean): 849
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 0.9714285714285714, 'subtotal_price': 0.9428571428571428, 'item_count': 0.9714285714285714}

### Failures (reported, never hidden)

- `truncated`: 15 (cord-val-004, cord-val-005, cord-val-007, cord-val-010, cord-val-012, cord-val-015, cord-val-018, cord-val-021, cord-val-022, cord-val-026)
- `wrong_value`: 2 (cord-val-044, cord-val-047)
