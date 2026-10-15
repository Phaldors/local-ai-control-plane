# M1 findings (validation split, 2026-10-15)

Host: MacBook Pro M5 Pro, 48 GB. Runtimes: Ollama 0.35 (`gemma4:26b`), mlx-lm server
(`mlx-community/Qwen3-8B-4bit`). Both behind one `LLMClient`, every call traced.
Prompts, golden sets and scorers are identical across runtimes. Reports: `docs/eval-reports/`.

| runtime / model | think | extraction pass | json valid | p50 latency | tool-call pass |
| --- | --- | --- | --- | --- | --- |
| ollama gemma4:26b | default | 33/50 (66%) | 70% (15 truncated) | 8967 ms | 25/25 |
| ollama gemma4:26b | off | 44/50 (88%) | 100% | 563 ms | 25/25 |
| mlx Qwen3-8B 4bit | default | 34/50 (68%) | 82% (9 truncated) | 10938 ms | 24/25 |
| mlx Qwen3-8B 4bit | off | 24/50 (48%) | 100% | 767 ms | 22/25 |

## What the numbers say
1. **Thinking is the dominant factor, not the model.** With default thinking and
   `max_tokens=1024`, gemma4 spends ~850 tokens to emit a ~40 token JSON; 30% of cases hit the
   limit and return nothing. Turning thinking off is ~16x faster (563 vs 8967 ms) and +22 points.
   A benchmark that did not report `truncated` separately would have blamed the model.
2. **Thinking helps the smaller model, not the larger one.** Qwen3-8B goes 48% -> 68% with
   thinking (subtotal/item_count get better); gemma4 gets no accuracy benefit from thinking
   among the cases that finish (field accuracy ~equal).
3. **Tool-call failures (reported, not hidden):** Qwen3-8B with thinking off made 3 `no_call`
   errors (tool-o1, tool-o4, tool-m3: it answered in text instead of calling a tool).
   With thinking on, 1 `wrong_args` (tool-c2: TRY vs TL currency code).
4. **MLX server does not enforce schemas.** `schema_enforced=False` for MLX. With thinking off,
   Qwen3-8B still produced 100% valid JSON, but this is measured, not guaranteed.

## Known issues (do not draw conclusions before fixing)
- **Golden label noise.** cord-val-004/021/022/036/047 are failed by *every* configuration.
  `item_count` labels derived from CORD `menu` look wrong when `menu` is a dict (expected 1,
  model counts 3-4) and `subtotal_price` is sometimes labelled equal to total where the
  receipt prints no subtotal. `total_price` is reliable (100% in the best configs).
  Action: audit these fields before M2, drop ambiguous cases or relabel.
- **Tool-call suite is too easy for gemma4** (25/25 in both modes). It still separates
  Qwen3-8B, but needs harder cases (multi-tool, ambiguous args, adversarial instructions).
- No RAM measurement yet; tok/s is runtime-reported (Ollama) or derived (MLX).
- Single run per config, temperature 0 / seed 0. No variance estimate yet.

## Router decision
Not justified yet. Evidence so far: for this task thinking-off gemma4 is both fastest and
best. A router needs at least two models that trade quality against cost on a clean golden
set; that needs the label audit and a third model first.
