# Harder task: multi-receipt extraction ladder (validation, 2026-10-15)

Task: 2, 4, 8 or 16 CORD receipts concatenated with only a separator line; return one total per
receipt, in order. 10 cases per size, seeded sampling, thinking off, max_tokens 1024, one run.
Reports: `docs/eval-reports/multi/`.

| model / runtime | pass | n=2 | n=4 | n=8 | n=16 | p50 / p95 |
| --- | --- | --- | --- | --- | --- | --- |
| gemma4:26b / Ollama | 40/40 | 100% | 100% | 100% | 100% | 1457 / 3067 ms |
| Qwen3-30B-A3B / MLX | 40/40 | 100% | 100% | 100% | 100% | 1771 / 3588 ms |
| Qwen3-8B / MLX | 34/40 | 90% | 100% | 70% | 80% | 2457 / 4916 ms |

Qwen3-8B failures: 5 `count_mismatch` (merged or split receipts, i.e. boundary detection) and
1 `wrong_value`. Both larger models made no mistakes at 16 receipts (~2k+ prompt tokens).

## What this says
1. **The task did not separate the two strong models**, so it is too easy to rank them; it only
   separates the small dense model. Ceiling effect, not proof that they are equal.
2. **No quality/cost trade-off appears.** The only model that fails is also the slowest here
   (dense 8B, p50 2457 ms vs 1457 ms for gemma4). Both stronger models are mixture-of-experts with
   few active parameters, which makes them faster than the dense 8B on this hardware.
3. **Qwen3-8B's accuracy is not monotonic in n** (n=8: 70%, n=16: 80%). With 10 cases per size that is
   noise; do not read a "difficulty curve" off a single model.
4. The one axis on which the 8B is cheaper is memory (4.6 GB vs 16.3 GB resident). That matters for
   running several models at once, not for single-request latency.

## Router decision (M3 revisited)
Still **not justified**. A router needs a cheaper option that is good enough on some inputs. Here the
cheaper-by-size model is neither faster nor good enough, and the strong models are saturated.
The honest framing for the portfolio: "I measured whether routing pays off, and on this hardware and
these tasks it does not". Revisit only with (a) a memory- or concurrency-bound scenario, (b) tasks
that are not saturated by the strong models (noisy OCR, multi-step tool use, adversarial input),
(c) an API-cost baseline (gpt-5-mini) to route against.
