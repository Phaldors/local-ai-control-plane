# Eval run 20261015T183703Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `multi_extraction` (40 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 2.8 GB
- commit: `2d4ac70`, host: arm64 / macOS-27.0-arm64-arm-64bit

## multi_extraction

- pass rate: **40/40 (100%)**
- latency p50/p95: 1771 ms / 3588 ms
- completion tokens (mean): 98
- 2 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 4 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 8 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 16 receipts: pass 100%, per-receipt accuracy 100% (10 cases)

### Failures (reported, never hidden)

None.
