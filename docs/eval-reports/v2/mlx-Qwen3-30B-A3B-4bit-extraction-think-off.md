# Eval run 20261015T181541Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 16.3 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **50/50 (100%)**
- latency p50/p95: 447 ms / 524 ms
- completion tokens (mean): 30
- JSON valid: 100%, schema valid: 100%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 1.0, 'item_count': 1.0}

### Failures (reported, never hidden)

None.
