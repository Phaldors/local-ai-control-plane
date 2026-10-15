# Eval run 20261015T164221Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: False
- commit: `4fe530a`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **24/50 (48%)**
- latency p50/p95: 767 ms / 1072 ms
- completion tokens (mean): 34
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.62, 'item_count': 0.84}

### Failures (reported, never hidden)

- `wrong_value`: 26 (cord-val-000, cord-val-001, cord-val-002, cord-val-003, cord-val-005, cord-val-006, cord-val-007, cord-val-009, cord-val-010, cord-val-012)
