# Eval run 20261015T200235Z-ollama-qwen3_30b-a3b

- runtime: `ollama`, model: `qwen3:30b-a3b`
- suite: `multi_extraction` (40 cases, split `validation`)
- max_tokens: 1024, think: False, guard: off
- resident model memory (approx): 21.3 GB
- commit: `d27159f`, host: arm64 / macOS-27.0-arm64-arm-64bit

## multi_extraction

- pass rate: **39/40 (98%)**
- latency p50/p95: 1417 ms / 3047 ms
- completion tokens (mean): 99
- 2 receipts: pass 90%, per-receipt accuracy 95% (10 cases)
- 4 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 8 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 16 receipts: pass 100%, per-receipt accuracy 100% (10 cases)

### Failures (reported, never hidden)

- `count_mismatch`: 1 (multi-n02-01)
