# Eval run 20261015T211341Z-ollama-qwen3_30b-a3b

- runtime: `ollama`, model: `qwen3:30b-a3b`
- suite: `extraction` (50 cases, split `validation`)
- max_tokens: 4096, think: None, guard: off
- resident model memory (approx): 21.3 GB
- reasoning leak: n/a (thinking not requested off)
- commit: `058fb5b`, host: arm64 / macOS-27.0-arm64-arm-64bit

## extraction

- pass rate: **48/50 (96%)**
- latency p50/p95: 14605 ms / 33692 ms
- completion tokens (mean): 1494
- JSON valid: 98%, schema valid: 98%
- field accuracy: {'total_price': 1.0, 'subtotal_price': 1.0, 'item_count': 0.9642857142857143}

### Failures (reported, never hidden)

- `truncated`: 1 (cord-val-002)
- `wrong_value`: 1 (cord-val-041)
