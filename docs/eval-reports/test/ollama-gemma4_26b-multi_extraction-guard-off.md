# Eval run 20261015T192835Z-ollama-gemma4_26b

- runtime: `ollama`, model: `gemma4:26b`
- suite: `multi_extraction` (40 cases, split `test`)
- max_tokens: 1024, think: False, guard: False
- resident model memory (approx): 1.4 GB
- commit: `e937f88`, host: arm64 / macOS-27.0-arm64-arm-64bit

## multi_extraction

- pass rate: **40/40 (100%)**
- latency p50/p95: 1445 ms / 3059 ms
- completion tokens (mean): 106
- 2 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 4 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 8 receipts: pass 100%, per-receipt accuracy 100% (10 cases)
- 16 receipts: pass 100%, per-receipt accuracy 100% (10 cases)

### Failures (reported, never hidden)

None.
