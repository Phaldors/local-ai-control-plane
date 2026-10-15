# M2 findings: three models, two runtimes, golden v2 (validation, 2026-10-15)

Host: MacBook Pro M5 Pro, 48 GB. Single run per configuration (temperature 0, seed 0, max_tokens 1024).
Golden v2: extraction labels audited (ambiguous `subtotal`/`item_count` labels dropped per case, 50 cases),
tool-call 37 cases (12 added: missing required args, decoys, number formats, enum synonyms).
Reports: `docs/eval-reports/v2/`. v1 reports are kept in `docs/eval-reports/v1/` and are not comparable.

| model / runtime | resident mem | thinking | extraction | tool-call | p50 / p95 extraction |
| --- | --- | --- | --- | --- | --- |
| gemma4:26b / Ollama | n/a | off | 49/50 | 36/37 | 551 / 648 ms |
| gemma4:26b / Ollama | n/a | default | 34/50 (15 truncated) | 37/37 | 8811 / 10933 ms |
| Qwen3-8B 4bit / MLX | 4.6 GB | off | 30/50 | 32/37 | 670 / 889 ms |
| Qwen3-8B 4bit / MLX | 4.6 GB | default | 40/50 (9 truncated) | 35/37 | 9717 / 18539 ms |
| Qwen3-30B-A3B 4bit / MLX | 16.3 GB | off | 50/50 | 34/37 | 447 / 524 ms |
| Qwen3-30B-A3B 4bit / MLX | 16.3 GB | default | 42/50 (7 truncated) | 34/37 | 5044 / 11775 ms |

Memory: MLX numbers are process RSS. Ollama's `/api/ps` size (1.4 GB for an 18 GB model) is not
trustworthy, so it is reported as n/a here.

## Findings
1. **Extraction needs no thinking.** The two strongest models reach 49-50/50 with thinking off at
   ~0.5 s p50. With thinking on, every failure except one `wrong_value` per model is `truncated`
   (budget exhausted), so accuracy among completed answers is equal. This run does not show thinking
   improving extraction for these models; it shows it making it slower and fragile under a token cap.
   Caveat: with a larger `max_tokens` thinking might finish; not tested.
2. **Tool-calling is where models differ.** Failures are real and reported: Qwen3-8B off has 4 `no_call`
   (answers in text instead of calling); Qwen3-30B-A3B has 2 `no_call` (off) or 2 `wrong_args` (on);
   gemma4 off has 1 `unexpected_call` (opened a ticket without a required `priority`), gemma4 with
   thinking is the only configuration at 37/37, at ~3x latency (1551 vs 495 ms).
3. **A bigger MoE model beat the dense one on both cost axes.** Qwen3-30B-A3B (16 GB, ~3B active) is
   faster than Qwen3-8B (4.6 GB) and far more accurate on extraction (50/50 vs 30/50).
4. **MLX does not enforce schemas** (`schema_enforced=False`), yet JSON validity was 100% whenever
   output was not truncated. Measured, not guaranteed.

## Limits of this evidence
- n=50/37, one run, one seed: differences of 1-2 cases (49 vs 50, 36 vs 37) are noise.
- Tool-call sample is small and hand-written by one author.
- Thinking-on runs capped at 1024 tokens.
- Test split untouched.

## M3 decision: is a router justified?
**No, not on this evidence.** For extraction the cheapest configuration (thinking off) is also the best,
so routing would have nothing to trade. The only quality/cost trade seen is thinking-on for tool-calls
(+1 case on gemma4, 3x latency), which is inside the noise. A router needs a task where a cheaper model
measurably fails and a stronger one measurably succeeds. Candidate next measurements before revisiting:
(a) thinking-on with `max_tokens` 4096, (b) 3+ seeds and a larger tool-call set to separate noise from signal,
(c) harder tasks (long documents, multi-step tool use, adversarial inputs from M5).
