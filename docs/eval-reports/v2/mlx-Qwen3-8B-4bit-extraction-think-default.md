# Eval run 20261015T180405Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: None
- resident model memory (approx): 4.6 GB
- commit: `4139493`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **40/50 (80%)**
- latency p50/p95: 9717 ms / 18539 ms
- completion tokens (mean): 601
- JSON valid: 82%, schema valid: 82%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.9705882352941176, 'item_count': 1.0}

### Failures (reported, never hidden)

- `truncated`: 9 (cord-val-007, cord-val-008, cord-val-016, cord-val-026, cord-val-031, cord-val-033, cord-val-038, cord-val-041, cord-val-045)
- `wrong_value`: 1 (cord-val-001)
