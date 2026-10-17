# AGENTS.md: Local AI Control Plane (handoff for Codex and other agents)

Read this first when working in this folder. The owner is Arda (talk to them in Turkish, direct and short). The
repo is public: `github.com/Phaldors/local-ai-control-plane`, branch `main`, tags `final-freeze` and `final-results`.
`README.md` is the overview, `docs/README.md` indexes every findings document, `PLAN.md` is the status.

## State (2026-10-16)
The project is **technically complete and documented**. All milestones are done except two deliberate non-goals
(router, CV wording). 130 Python tests and 21 frontend tests pass, `ruff` is clean, CI is green. Nothing is half-done in the working tree.
What exists: two runtimes behind one `LLMClient`, JSONL tracing, six golden suites, an agent loop over a deterministic
fake shop, a policy guard with PII redaction, audit log and human escalation, an independent security oracle, a
regression gate with committed baselines, a one-page dashboard, a reasoning-leak check, a one-shot test-split protocol
that was executed once (see `docs/final-report.md`).

## MCP layer (added 2026-10-17)
`controlplane/mcp_server.py` serves the shop tools over MCP with the rule guard enforced server-side; `mcp_client.py`'s `McpWorld`
runs the suites through the protocol (`--transport mcp`). Behind MCP, `--guard provenance` runs in the *host* adapter (the server never
sees the user's words). Never add an approval tool: escalations are a read-only resource. Install with `uv sync --group mcp`. Findings,
including that how tool schemas are written changed an injection outcome 0/8 -> 8/8 on one case for gemma4 (not reproduced on three other
model configurations; sampled injection rates are ~1-4%, not 0), are in `docs/mcp.md`. Scripts:
`scripts/injection_rate.py` (sampled), `scripts/schema_bisect.py`. Evaluate the *served* schemas, not the hand-written ones.

## Escalation console (added 2026-10-17)
`controlplane/escalations.py` (SQLite queue + append-only event log), `backoffice.py` (re-checks hard policy at approval time),
`console_api.py` (FastAPI, token-protected human channel), `console/` (React + TypeScript, `pnpm`). The model must never reach `decide`:
it is not an MCP tool and `mcp_server.py` must not import the console (a test enforces it). Install with `uv sync --group console` and
`make console-install`; demo with `make console-demo` (needs `CONSOLE_TOKEN`). Optional groups stay optional: core modules must not
import `fastapi` or `mcp`. Details and limits in `docs/console.md`.

## Commands
```bash
uv sync && uv run pytest -q && uv run ruff check .          # or: make check
uv run python -m controlplane.cli eval --runtime ollama --model gemma4:26b --suite agent_security --guard on --think off
uv run python -m controlplane.cli gate runs/<run_dir>        # compares with baselines/, exit 1 = regression
uv run python -m controlplane.cli dashboard                  # writes docs/dashboard.html
uv run python -m scripts.compare_runs --a mlx:<model_key> --b ollama:<model_key> [--max-tokens N]
uv run python -m scripts.scan_reasoning_leak                 # leak rate per think-off config
```
Runtime values: `ollama`, `mlx`, `ollama-nothink`. Guard values: `off`, `on` (rules), `provenance`. Suites: `extraction`,
`multi_extraction`, `tool_call`, `agent`, `agent_security`, `agent_injection`, or `all`.

## Environment on Arda's machine (MacBook Pro M5 Pro, 48 GB, Python 3.12 via uv)
- Ollama runs at `localhost:11434`: `gemma4:26b` (18 GB) and `qwen3:30b-a3b` (18.6 GB, **this tag is Qwen3-30B-A3B-Thinking-2507**,
  a reasoning-only checkpoint; its `think=false` is ignored).
- MLX models are in the Hugging Face cache (38 GB): `mlx-community/Qwen3-8B-4bit`, `Qwen3-30B-A3B-4bit` (the original **hybrid**,
  has `enable_thinking`), `Qwen3-30B-A3B-Thinking-2507-4bit`. Start one with
  `uv run mlx_lm.server --model mlx-community/<name> --port 8080` and stop it afterwards (`pkill -f mlx_lm.server`).
  Do not run two large models while timing matters. `uv sync --group mlx` for MLX, `--group build` for the CORD builders.
- `runs/` is **gitignored and local only** (raw run directories with traces). Reports worth keeping are copied into
  `docs/eval-reports/<stage>/`. The CORD-v2 dataset is read from the Hugging Face cache (`HF_HUB_OFFLINE=1`).

## Layout
`controlplane/` (client, runtimes, tracing, agent loop, `worlds/shop.py`, `guard.py`, `audit.py`, `redaction.py`,
`reasoning.py`, `gate.py`, `dashboard.py`, `evals/` contract, scorers, agent scorer, runner), `golden/*.jsonl`,
`scripts/build_golden_*.py` (golden files are generated, do not hand-edit them), `baselines/` (committed gate baselines),
`tests/`, `docs/`.

## Hard rules
1. **The test split is spent.** Do not run `--split test` again. The CLI requires `--confirm-final` and refuses a repeat
   of the same configuration; never use `--allow-rerun` to improve a number. The `agent_injection` test split is the only
   unspent one: use it once, and only after an attack exists that makes the guard modes distinguishable.
2. **Do not change validation cases.** If a golden builder changes, regenerate and verify that the validation cases are
   content-identical to what was measured (a past mistake: a lint-driven wording change made the file differ from the
   measured text). Changing a golden set demands a deliberate re-baseline (the gate enforces it).
3. **Check checkpoint identity before calling two runs "the same model"** (`ollama show`, `/api/show` model_info and template,
   `config.json` and the chat template for MLX). A claim to the contrary was retracted once.
4. **Report n with every number, report failures, and keep corrections visible.** Never hide a failing case or tune on test.
5. **Downloads need Arda's explicit yes** with source, name and size stated. **Never put API keys in chat or files**; keys
   belong in `.env` (gitignored).
6. **Commits:** small and logical, never amend, do not commit `runs/`, `.env`, `.venv/`. Run `make check` before pushing.
7. Do not apply to jobs for Arda and do not touch CV or LinkedIn text unless Arda asks. FERASET and Gulliver's Games are
   permanently dropped: no notes, follow-ups or reminders for them.

## What the results support, and what they do not
Supported: a code-level guard takes executed violations and leaks to 0 for three local models without measured loss of
legitimate actions (test split, n=14 for the security suite, expectations #4 to #6 held); thinking budget dominates
structured extraction; no router was justified; the Thinking-2507 checkpoint behaves alike on MLX and Ollama
(28/29 vs 27/29 agent suite).
Not supported: any claim that the provenance guard improves security (no attack succeeded, only its cost was seen);
"gemma4 is more accurate than Qwen3" (confounded by reasoning on/off and checkpoint); model-quality statements from the
Qwen3 rows on MLX thinking-off; robustness against prompt injection in general (three small models, toy world).

## Pitfalls already hit (save yourself the time)
- Search-and-replace patches silently fail after `ruff format` reflows code; assert the match and re-read the file.
- `zsh` does not word-split `$VAR`: use functions. macOS `sed -i` needs an extension argument.
- Baseline identity excludes `max_tokens` on purpose (a lower `max_tokens` is a regression, not a new config).
- Reasoning models need `max_tokens` around 4096 or they truncate; `think` flags are runtime and checkpoint specific, so
  read `reasoning leak` in reports and tokens per call, not the label.
- A background monitor that greps only for success stays silent on a crash; include failure signatures.
- Optional dependency groups (`mcp`, `mlx`, `build`) must never be imported by core modules: a local env with every group
  installed hid a CI break once. Before pushing, mimic CI with `uv sync && uv run pytest -q` (MCP tests then skip), and
  restore with `uv sync --group mcp --group mlx --group build`. CI installs `--group mcp`.

## Open items (all optional, none blocking)
1. Run the original hybrid on Ollama (`qwen3:30b-a3b-q4_K_M`, 18.6 GB, metadata verified as the hybrid: context 40,960, no
   `finetune: Thinking`) to separate reasoning from checkpoint. Needs Arda's download approval.
2. `qwen3:8b` on Ollama to check whether Qwen3-8B (MLX) has the same thinking-off tool-use failure.
3. gpt-5-mini API baseline (key via `.env`).
4. A stronger attack (larger model, multi-turn, other channels) to make the provenance guard measurable; then spend the
   `agent_injection` test split once.
5. CV and LinkedIn wording for this project: only when Arda asks.
Recommended next step from the last session: stop adding experiments and return to job search tasks Arda chooses.

## Memory protocol (ArdaOS vault)
This folder lives in the ArdaOS vault. After meaningful work update `🔮 850-Companion/Last-Session.md` and `Threads.md`
(vault root `AGENTS.md` explains the rest).
