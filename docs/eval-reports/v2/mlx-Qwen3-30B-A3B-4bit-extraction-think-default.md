# Eval run 20261015T181620Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: None
- resident model memory (approx): 16.3 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **42/50 (84%)**
- latency p50/p95: 5044 ms / 11775 ms
- completion tokens (mean): 578
- JSON valid: 86%, schema valid: 86%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 1.0, 'item_count': 0.9565217391304348}

### Failures (reported, never hidden)

- `truncated`: 7 (cord-val-000, cord-val-004, cord-val-018, cord-val-026, cord-val-028, cord-val-038, cord-val-043)
- `wrong_value`: 1 (cord-val-041)
