# Eval run 20261015T164321Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 1024, think: None
- commit: `4fe530a`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **34/50 (68%)**
- latency p50/p95: 10938 ms / 20878 ms
- completion tokens (mean): 601
- JSON valid: 82%, schema valid: 82%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.926829268292683, 'item_count': 0.9024390243902439}

### Failures (reported, never hidden)

- `truncated`: 9 (cord-val-007, cord-val-008, cord-val-016, cord-val-026, cord-val-031, cord-val-033, cord-val-038, cord-val-041, cord-val-045)
- `wrong_value`: 7 (cord-val-001, cord-val-002, cord-val-004, cord-val-021, cord-val-022, cord-val-036, cord-val-047)
