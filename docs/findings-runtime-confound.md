# Qwen3-30B-A3B on Ollama vs MLX: what the comparison does and does not show (2026-10-15)

> **Correction made later the same day.** This page first claimed "same model, two runtimes". That was wrong.
> The Ollama tag `qwen3:30b-a3b` is **Qwen3-30B-A3B-Thinking-2507** (metadata: `general.finetune: Thinking`,
> version 2507, context 262,144, a reasoning-only checkpoint whose template has no off switch). The MLX model
> `mlx-community/Qwen3-30B-A3B-4bit` is the **original hybrid** Qwen3-30B-A3B (context 40,960, chat template with
> `enable_thinking`). The two runs differ in checkpoint, quantization (GGUF Q4_K_M vs MLX 4-bit), chat template and
> reasoning, all at once. Claims that need one variable changed at a time are withdrawn below.

Reports and trajectories: `docs/eval-reports/runtime-confound/` (the Ollama runs). Paired comparison:
`scripts/compare_runs.py`. Validation split only (the test split was spent in the final run).

## What was compared
Hybrid Qwen3-30B-A3B on MLX with thinking off (earlier runs) against Qwen3-30B-A3B-Thinking-2507 on Ollama with
`think=false` requested.

| suite | MLX hybrid, thinking off | Ollama Thinking-2507 | discordant pairs (MLX-only / Ollama-only) | sign-test p |
| --- | --- | --- | --- | --- |
| agent (29) | 19/29 | **27/29** | 1 / 9 | 0.02 |
| agent_security, guard off (21) | 11/21 | **17/21** | 0 / 6 | 0.03 |
| agent_injection, guard off (10) | 7/10 | 8/10 | 2 / 3 | 1.00 |
| tool_call (37) | 34/37 | 35/37 | 1 / 2 | 1.00 |
| extraction (50) | 50/50 | 47/50 | 3 / 0 | 0.25 |
| multi_extraction (40) | 40/40 | 39/40 | 1 / 0 | 1.00 |

The two tool-use suites differ significantly. Cost differs too: agent suite p50 1.1 s and 71 tokens per case on MLX,
6.4 s and 802 tokens on Ollama.

## What is supported
1. **On MLX, the hybrid checkpoint with `enable_thinking=false` fails at tool use in a recognisable way.** The raw
   server response to "Please refund order O-1006 in full." is plain text with `finish_reason: stop` and no tool call
   ("I will issue a full refund for order O-1006. Let me process that for you."): the model announces the action and
   stops. The same server without the flag returns a correct `get_order` call. This matches the MLX agent
   trajectories (price invented without `get_product`, "let me retrieve the order" and nothing else). This
   observation concerns the hybrid checkpoint under that template path.
2. **On Ollama, the Thinking-2507 checkpoint reasons whatever `think` says.** With `think=false` the reasoning is
   returned as visible content ("Okay, let's see. The user wants a refund...", 227 tokens); with `think=true` it is in
   the `thinking` field. gemma4 on the same server honours the flag (22 tokens, no reasoning). Adding Qwen3's
   `/no_think` soft switch (the `ollama-nothink` runtime variant) did not change that: 294 and 244 tokens on two
   test prompts, because this checkpoint has no such switch.
3. **At matched reasoning behaviour on one runtime, gemma4 and the Thinking-2507 checkpoint are not distinguishable**
   (both on Ollama, paired on identical cases: agent 28 vs 27, security 17 vs 17, injection 10 vs 8, tool_call 36 vs 35,
   extraction 49 vs 47, multi-receipt 40 vs 39; every sign-test p >= 0.5). gemma4 gets there at p50 1.1 s without
   reasoning against 6.4 s for the reasoning-only checkpoint.

## What is withdrawn
- "Same model on two runtimes", and therefore "the gap is not a runtime-quality difference" and "the `think` flag is not
  portable": none of these can be concluded, because the checkpoint changed. (The flag did work for the hybrid on MLX
  and does work for gemma4 on Ollama; it cannot work for a checkpoint that always reasons.)
- The earlier statement that the MLX/Ollama gap isolates reasoning on/off. It mixes checkpoint, reasoning,
  quantization and template.

## Consequences for earlier documents
- **Final report / M4:** the Qwen3 rows (MLX, hybrid, thinking off) stand as measurements of that configuration. Their
  weakness on tool use is tied to the MLX thinking-off path for the hybrid checkpoint (point 1), not shown to be a
  property of Qwen3-30B-A3B in general. The pre-registered numbers are unchanged. Qwen3-8B (MLX) very likely shares
  the thinking-off tool-use failure and was not re-run.
- The router conclusion is unaffected.

## How to separate the variables (not done)
Run the same checkpoint on both runtimes: `mlx-community/Qwen3-30B-A3B-Thinking-2507-4bit` on MLX (reasoning always on)
against the Ollama tag, or the original hybrid on Ollama (`ollama pull` of a hybrid tag) against the MLX hybrid, in
both cases with reasoning set the same way. Each needs a model download.

## The leak detector (still valid)
`controlplane/reasoning.py` flags an answer that starts with a reasoning opener followed by first-person planning
language. Counts go to traces, run metadata, the report and a dashboard column, and the gate fails when more than 10%
of think-off calls leak and the baseline did not. On all think-off runs in `runs/`: MLX Qwen3-30B 0/638, MLX Qwen3-8B
0/768, Ollama gemma4 0/1445, Ollama Thinking-2507 282/373 (76%; 282 of 283 calls in the tool-use suites, 0 of 90 in the
schema-constrained extraction suites). Live check: a fresh gemma4 tool-call run is 0/37 and passes the gate; the same
suite on the Thinking-2507 checkpoint is 37/37, scores 35/37, and fails the gate (`config.reasoning_leak`, latency
2242 vs 491 ms, tokens 55 -> 245), so it catches a cost/label mismatch that accuracy does not show. The detector
measures leakage into content with English openers only. Its real finding here is that a reasoning-only checkpoint
ignores "thinking off"; it works as designed, on a different cause than first reported.

## Limits
n=10 to 50, single runs, validation only; sign tests on discordant pairs have little power.
