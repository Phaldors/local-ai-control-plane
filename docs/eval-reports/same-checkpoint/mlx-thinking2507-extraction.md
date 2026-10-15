# Eval run 20261015T205251Z-mlx-mlx-community_Qwen3-30B-A3B-Thinking-2507-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-Thinking-2507-4bit`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 4096, think: None, guard: off
- resident model memory (approx): 16.3 GB
- reasoning leak: n/a (thinking not requested off)
- commit: `058fb5b`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **45/50 (90%)**
- latency p50/p95: 10282 ms / 32098 ms
- completion tokens (mean): 1164
- JSON valid: 98%, schema valid: 98%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 0.9024390243902439, 'item_count': 1.0}

### Failures (reported, never hidden)

- `truncated`: 1 (cord-val-002)
- `wrong_value`: 4 (cord-val-006, cord-val-010, cord-val-018, cord-val-024)
