# Eval run 20261015T183514Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `multi_extraction` (40 cases, split `validation`)
- max_tokens: 1024, think: False
- resident model memory (approx): 3.0 GB
- commit: `2d4ac70`, host: arm64 / macOS-27.0-arm64-arm-64bit

## multi_extraction

- pass rate: **34/40 (85%)**
- latency p50/p95: 2457 ms / 4916 ms
- completion tokens (mean): 116
- 2 receipts: pass 90%, per-receipt accuracy 95% (10 cases)
- 4 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 8 receipts: pass 70%, per-receipt accuracy 75% (10 cases)
- 16 receipts: pass 80%, per-receipt accuracy 95% (10 cases)

### Failures (reported, never hidden)

- `count_mismatch`: 5 (multi-n02-05, multi-n08-00, multi-n08-01, multi-n08-08, multi-n16-03)
- `wrong_value`: 1 (multi-n16-09)
