# Eval run 20261015T193135Z-mlx-mlx-community_Qwen3-30B-A3B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-30B-A3B-4bit`
- suite: `multi_extraction` (40 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 16.3 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## multi_extraction

- pass rate: **31/40 (78%)**
- latency p50/p95: 1421 ms / 2983 ms
- completion tokens (mean): 101
- 2 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 4 receipts: pass 90%, per-receipt accuracy 98% (10 cases)
- 8 receipts: pass 70%, per-receipt accuracy 88% (10 cases)
- 16 receipts: pass 50%, per-receipt accuracy 97% (10 cases)

### Failures (reported, never hidden)

- `count_mismatch`: 2 (multi-test-n08-04, multi-test-n08-08)
- `wrong_value`: 7 (multi-test-n04-06, multi-test-n08-06, multi-test-n16-01, multi-test-n16-02, multi-test-n16-03, multi-test-n16-04, multi-test-n16-08)
