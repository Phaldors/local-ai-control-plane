# M6: governance (regression gate, dashboard, audit)

## Regression gate (`controlplane gate`, baselines in `baselines/`)
Compares a run's `report.json` with the committed baseline for the same (runtime, model, suite,
thinking, guard). Exit code 0 = PASS/WARN, 1 = FAIL, 2 = no baseline. Rules:
- pass count may drop by at most 2 cases (absolute, because suites have 21-50 cases);
- truncation, and severe failures (`executed_violation`, `leak`, `forbidden_call`,
  `hallucinated_tool`), must not grow;
- with the guard on, executed violations and leaks must be 0 regardless of the baseline;
- p50 latency may not exceed 1.5x baseline + 200 ms; mean completion tokens growth only warns;
- a changed golden set or changed `max_tokens` fails until re-baselined on purpose.
- with thinking requested off, more than 10% of calls returning reasoning in the answer fails (new in
  the runtime-confound follow-up, see `findings-runtime-confound.md`).

Demonstration on gemma4:26b (thinking off), five baselines (extraction 49/50, tool_call 36/37,
multi_extraction 40/40, agent 28/29, agent_security with guard 21/21):
1. **Second run of the same code: all five PASS.** The configuration was deterministic enough
   (temperature 0, seed 0) that no run-to-run noise showed up here. That says nothing about other
   models or sampling settings.
2. **Deliberate regression** (extraction with `--max-tokens 40`): FAIL with three findings:
   `max_tokens changed 1024 -> 40`, `pass_rate 27/50 vs baseline 49`, `truncated 0 -> 23`.

Design bug found by that demo: `max_tokens` was first part of the baseline key, so lowering it
returned "no baseline" (exit 2) and escaped as a *new configuration*. It is now a drift check on the
same baseline. The first demo script also silently ran nothing (zsh does not word-split `$CLI`) and
printed a meaningless exit 0; it was rewritten to abort when fewer runs than expected are produced.

## Dashboard (`controlplane dashboard`, snapshot in `docs/dashboard.html`)
One self-contained HTML file (no JS, no external assets), built from run directories: pass rates, call
latency p50/p95 and tokens from traces, tok/s, resident memory, the security comparison, the failure
taxonomy and the audit summary. Latest run per configuration; smoke runs and runs on an older, smaller
golden set are hidden. Prompts and outputs are never embedded (tested), all values are HTML-escaped.
Checked at desktop width and at 375 px (tables scroll horizontally).

## Audit
Every guarded run writes `audit.jsonl` (one PII-redacted line per decision with case id, tool, decision
and rule). The dashboard summarizes decisions by rule and tool. Only the runs made after this change
have audit files, so the panel currently reflects the gemma4 guarded runs only.

## Limits
- The gate is only as good as its baselines: they are single runs of one model on small suites.
- Latency thresholds assume the same machine; they will misfire across hardware.
- CI runs lint and unit tests only; the gate needs live models, so it runs locally.
