# Eval run 20261015T193348Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `extraction` (50 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 4.6 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **27/50 (54%)**
- latency p50/p95: 685 ms / 856 ms
- completion tokens (mean): 34
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.5384615384615384, 'item_count': 0.8}

### Failures (reported, never hidden)

- `wrong_value`: 23 (cord-test-001, cord-test-006, cord-test-011, cord-test-012, cord-test-013, cord-test-015, cord-test-017, cord-test-018, cord-test-021, cord-test-022)
