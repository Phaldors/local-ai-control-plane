# Eval run 20261015T180300Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 4.6 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **30/50 (60%)**
- latency p50/p95: 670 ms / 889 ms
- completion tokens (mean): 34
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.5476190476190477, 'item_count': 0.9285714285714286}

### Failures (reported, never hidden)

- `wrong_value`: 20 (cord-val-000, cord-val-001, cord-val-006, cord-val-009, cord-val-010, cord-val-012, cord-val-016, cord-val-018, cord-val-019, cord-val-024)
