# Separating model from runtime: Qwen3-30B-A3B on Ollama vs MLX (validation, 2026-10-15)

Since M4 the comparison "gemma4 (Ollama) vs Qwen3 (MLX)" mixed model and runtime. To separate them,
`qwen3:30b-a3b` (Ollama default build, GGUF Q4_K_M, 18.6 GB, pulled with approval) was run on the validation
suites with thinking requested off, and compared with the earlier MLX 4-bit runs of the same model.
Reports and trajectories: `docs/eval-reports/runtime-confound/`. Paired comparison: `scripts/compare_runs.py`.
The test split is not used (it was spent in the final run).

## Result 1: tool-use suites differ a lot between the two runtimes; single-turn suites do not
| suite | MLX 4-bit | Ollama Q4_K_M | discordant pairs (MLX-only / Ollama-only) | sign-test p |
| --- | --- | --- | --- | --- |
| agent (29) | 19/29 | **27/29** | 1 / 9 | 0.02 |
| agent_security, guard off (21) | 11/21 | **17/21** | 0 / 6 | 0.03 |
| agent_injection, guard off (10) | 7/10 | 8/10 | 2 / 3 | 1.00 |
| tool_call (37) | 34/37 | 35/37 | 1 / 2 | 1.00 |
| extraction (50) | 50/50 | 47/50 | 3 / 0 | 0.25 |
| multi_extraction (40) | 40/40 | 39/40 | 1 / 0 | 1.00 |

## Result 2: the cause is what "thinking off" does, not the runtime's quality
Latency and tokens for the same model (thinking requested off): agent suite p50 **1.1 s / 71 tokens** on MLX vs
**6.4 s / 802 tokens** on Ollama; tool_call 0.4 s / 30 tokens vs 2.1 s / 245 tokens. Direct checks on one prompt
("Please refund order O-1006 in full."):
- **MLX, `enable_thinking=false`:** the raw server response is plain text, `finish_reason: stop`, no tool call:
  "I will issue a full refund for order O-1006. Let me process that for you." The model announces the action and
  stops. This is exactly the failure seen across the MLX agent trajectories (price invented without
  `get_product`, "I will process the refund, let me retrieve the order", asking for facts it could look up).
  Without that flag the same server returns a correct `get_order` tool call (reasoning on).
- **Ollama, `think=false` on `qwen3:30b-a3b`:** reasoning is **not** suppressed. It leaks into the visible content
  ("Okay, let's see. The user wants a refund for order O-1006...", 227 tokens) and the call is then made
  correctly. gemma4 with the same flag answers in 22 tokens with the call and no reasoning.
So "thinking off" means truly off on MLX and "reasoning leaked into content" on Ollama for this model. The
27/29 vs 19/29 gap is **reasoning on vs off for tool use**, not a runtime-quality difference.

## Result 3: on the same runtime, gemma4 and Qwen3-30B-A3B are not distinguishable
Both on Ollama, thinking requested off, paired on identical cases: agent 28 vs 27, security 17 vs 17, injection 10 vs 8,
tool_call 36 vs 35, extraction 49 vs 47, multi-receipt 40 vs 39; every sign-test p >= 0.5. What differs is
cost: gemma4 reaches 28/29 on the agent suite at p50 1.1 s with no reasoning, Qwen3-30B-A3B reaches 27/29 at p50 6.4 s
because it reasons in the content.

## Corrections to earlier conclusions
- **M4 (`findings-m4.md`):** "failures are real behaviour, not formatting" was too strong. They are real model outputs,
  but produced under the MLX thinking-off template path that makes Qwen3 announce an action and stop.
- **Final report:** the Qwen3 rows on the agent and security suites (and the claim that gemma4 is the most accurate on
  every suite) are confounded by this effect; at a matched, working configuration the two models are not
  distinguishable on these suites. The pre-registered numbers are unchanged and were not re-run.
- **Qwen3-8B** (MLX only) very likely shares the artifact; it was not re-run (no `qwen3:8b` pulled).
- The router conclusion is unaffected: a cheaper tier that works would still need to beat gemma4 on cost, and the
  only cheap Qwen3 configuration (thinking truly off) fails tool use.

## Limits
- Quantization differs (MLX 4-bit vs GGUF Q4_K_M), as do chat templates and tool-call parsers; this experiment
  separates "reasoning on/off" from nothing else cleanly. A third configuration (Ollama with reasoning really off, or
  MLX with reasoning on at a bounded budget) would be needed to isolate the template from the quantization.
- n=10 to 50, single runs, validation only; p-values come from a sign test on discordant pairs with little power.

## What changes in the project
The `think` flag is not portable across runtimes. Reports should be read together with effective completion tokens
(mean tokens per case), which expose leaked reasoning, and a future gate rule could flag "think off but tokens high".

## Follow-up: a reasoning-leak check in the gate (added the same day)
`controlplane/reasoning.py` flags an answer that starts with a reasoning opener ("Okay, let's see. The user wants...",
"Hmm, ...", "Let me think...") followed by first-person planning language. Every call made with thinking requested off is
checked; counts go to the trace (`reasoning_leak`), the run metadata and the markdown report, the dashboard has a `leak`
column, and the gate fails when more than 10% of think-off calls leak and the baseline did not (warns when the baseline
already leaked: the flag is simply not effective for that model/runtime).

Validation of the detector on all existing think-off runs (`python -m scripts.scan_reasoning_leak`):

| runtime | model | think-off calls | flagged | rate |
| --- | --- | --- | --- | --- |
| MLX | Qwen3-30B-A3B-4bit | 638 | 0 | 0% |
| MLX | Qwen3-8B-4bit | 768 | 0 | 0% |
| Ollama | gemma4:26b | 1408 | 0 | 0% |
| Ollama | qwen3:30b-a3b | 336 | 245 | 73% |

For qwen3:30b-a3b the flags are 100% of calls in every tool-use suite (294 of 295 calls in the agent, security and
injection suites, 37/37 in tool-call) and 0 in the two schema-constrained extraction suites, where the output format leaves
no room for prose. Unit tests include normal answers that start with "Okay" (e.g. "Okay, the order is pending.") that
must not be flagged. Live check: a fresh gemma4 tool-call run is 0/37 and passes the gate; the same suite on
qwen3:30b-a3b is 37/37, scores 35/37 (accuracy hardly changes) and **fails** the gate with `config.reasoning_leak`
plus latency 2242 vs 491 ms and tokens 55 -> 245. The check therefore catches a cost/label mismatch that accuracy
alone does not show.

Limits: the detector is a narrow pattern matcher (English openers); other styles of leaked reasoning, or a model
that reasons without such openers, would be missed. It measures leakage into content, not hidden reasoning tokens.
