# Eval run 20261015T193424Z-mlx-mlx-community_Qwen3-8B-4bit

- runtime: `mlx`, model: `mlx-community/Qwen3-8B-4bit`
- suite: `multi_extraction` (40 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 4.6 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## multi_extraction

- pass rate: **29/40 (72%)**
- latency p50/p95: 2452 ms / 5725 ms
- completion tokens (mean): 126
- 2 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 4 receipts: pass 80%, per-receipt accuracy 85% (10 cases)
- 8 receipts: pass 50%, per-receipt accuracy 72% (10 cases)
- 16 receipts: pass 60%, per-receipt accuracy 79% (10 cases)

### Failures (reported, never hidden)

- `count_mismatch`: 10 (multi-test-n04-05, multi-test-n04-06, multi-test-n08-02, multi-test-n08-04, multi-test-n08-06, multi-test-n08-07, multi-test-n08-08, multi-test-n16-00, multi-test-n16-01, multi-test-n16-05)
- `wrong_value`: 1 (multi-test-n16-07)
