# Eval run 20261015T192805Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `extraction` (50 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 1.4 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **47/50 (94%)**
- latency p50/p95: 546 ms / 638 ms
- completion tokens (mean): 41
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.9487179487179487, 'item_count': 0.9666666666666667}

### Failures (reported, never hidden)

- `wrong_value`: 3 (cord-test-013, cord-test-018, cord-test-031)
