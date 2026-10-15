# Eval run 20261015T193112Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `extraction` (50 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 16.3 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **42/50 (84%)**
- latency p50/p95: 450 ms / 547 ms
- completion tokens (mean): 31
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.9487179487179487, 'item_count': 0.8}

### Failures (reported, never hidden)

- `wrong_value`: 8 (cord-test-013, cord-test-018, cord-test-031, cord-test-033, cord-test-038, cord-test-041, cord-test-047, cord-test-052)
