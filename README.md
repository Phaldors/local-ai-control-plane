# Local AI Control Plane

Measure local LLMs the way you would before trusting them with private data.
One `LLMClient` interface in front of **Ollama** and **MLX-LM**, every call traced,
and a golden eval contract that reports failures instead of hiding them.

Status: **M1-M5 done** (two runtimes, tracing, five golden suites, agent loop with trajectory scoring,
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
