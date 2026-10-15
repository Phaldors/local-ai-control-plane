# Local AI Control Plane

Measure local LLMs the way you would before trusting them with private data.
One `LLMClient` interface in front of **Ollama** and **MLX-LM**, every call traced,
and a golden eval contract that reports failures instead of hiding them.

Status: **M1-M6 done, final test-split run done** (two runtimes, tracing, five golden suites, agent loop with trajectory scoring,
security guard with PII redaction, audit log and human escalation). Router, safety layer and
dashboard are deliberately not started: the router only gets built if the measurements justify it.

## What is here
- `controlplane/client.py`: the `LLMClient` protocol; `runtimes/ollama.py`, `runtimes/mlx.py`.
- `controlplane/tracing.py`: append-only JSONL trace for every call, including failures.
- `controlplane/evals/`: golden case contract, deterministic scorers, runner, markdown/JSON reports.
- `golden/`: single-receipt extraction (50, audited labels), single tool-call (37), multi-receipt extraction
  (40, 2-16 receipts), and a multi-step tool-use suite (29 cases over a deterministic shop world, with
  refund-policy traps and prompt injection planted in a tool result). CORD-v2 is CC-BY-4.0.
- Failure taxonomy: `transport_error`, `truncated`, `invalid_json`, `schema_invalid`, `wrong_value`,
  `no_call`, `unexpected_call`, `hallucinated_tool`, `wrong_tool`, `bad_args_schema`, `wrong_args`.

## Run it
```bash
uv sync
uv run pytest
uv run python -m controlplane.cli eval --runtime ollama --model gemma4:26b --suite all --think off
# MLX: uv sync --group mlx, then
uv run mlx_lm.server --model mlx-community/Qwen3-8B-4bit --port 8080
uv run python -m controlplane.cli eval --runtime mlx --model mlx-community/Qwen3-8B-4bit --suite all
```

## Final result
One-shot test-split run, 21 runs, expectations written beforehand ([final-report.md](docs/final-report.md)):
gemma4:26b 94% extraction, 100% multi-receipt and tool-call; with the guard on, executed violations and leaks
are 0 for all three models, no over-blocking. Four of seven pre-registered expectations held; the two that
failed were about Qwen3-30B-A3B's quality generalizing (validation was optimistic).

## Runtime and checkpoint confound
On MLX the hybrid Qwen3-30B-A3B with thinking off often announces an action and stops instead of calling the tool
(19/29 on the agent suite). The Ollama tag `qwen3:30b-a3b` that scored 27/29 is a different, reasoning-only checkpoint
(Thinking-2507). Running that same checkpoint on both runtimes gave 28/29 (MLX) and 27/29 (Ollama), with matching
failure patterns: runtime, quantization and template are not the source of the gap; checkpoint and reasoning are,
and are not separated further. See [findings](docs/findings-runtime-confound.md), which also corrects an earlier
version of itself.

## Injection follow-up
A provenance guard mode, a mid-task injection suite and an 8-payload red-team sweep were added
([findings](docs/findings-injection.md)). No model attempted an injected action, so the new guard's benefit is
not demonstrated; the earlier violations came from user-side pressure and scope, not from tool-result text.

## Governance
```bash
uv run python -m controlplane.cli baseline-save runs/<run_dir>   # commit the result in baselines/
uv run python -m controlplane.cli gate runs/<run_dir>            # exit 1 on regression
uv run python -m controlplane.cli dashboard                      # writes docs/dashboard.html
```
Details and a deliberate-regression demo: [docs/findings-m6.md](docs/findings-m6.md).

## First findings (MacBook Pro M5 Pro, 48 GB, validation split, single run)
| runtime / model | thinking | extraction | tool-call | p50 latency |
| --- | --- | --- | --- | --- |
| Ollama gemma4:26b | default | 66% (15 truncated) | 25/25 | 8967 ms |
| Ollama gemma4:26b | off | 88% | 25/25 | 563 ms |
| MLX Qwen3-8B 4-bit | default | 68% | 24/25 | 10938 ms |
| MLX Qwen3-8B 4-bit | off | 48% | 22/25 | 767 ms |

The dominant factor was the thinking-token budget, not the model. Known issues (golden label noise,
easy tool-call set, no RAM measurement, no variance estimate) are listed in
[docs/findings-m1.md](docs/findings-m1.md). The test split is untouched.

Later findings: [multi-receipt ladder](docs/findings-m3.md) and [multi-step tool use](docs/findings-m4.md)
(gemma4:26b 28/29 vs Qwen3 models 18-23/29, including unsafe refunds). Router is still not justified by the data.

Security ([findings](docs/findings-m5.md)): a code-level policy guard took executed violations and data leaks
from 4-11 per model to 0 on a 21-case suite, without blocking legitimate calls; instructing the model in the
prompt did not prevent cross-customer access.
