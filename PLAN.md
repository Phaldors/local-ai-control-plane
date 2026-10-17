---
title: Local AI Control Plane Plan
created: 2026-10-15
modified: 2026-10-16
type: project
status: active
tags: [project, local-llm, ollama, mlx, eval, security, llmops]
---

# Local AI Control Plane: status

Goal: measure local LLMs the way you would before trusting them with private data, with the policy in code.
Constraints set by Arda: Ollama and MLX-LM behind one `LLMClient`; failures are findings, not hidden; a router only
if measurements justify it.

## Milestones
- [x] M1 `LLMClient`, Ollama and MLX runtimes, JSONL trace, golden contract, failure taxonomy
- [x] M2 three models, audited labels (golden v2), thinking on/off
- [x] M3 router decision: not justified (re-checked on multi-receipt and multi-step tool use)
- [x] M5 security: policy guard, PII redaction, audit, escalation, independent oracle
- [x] M6 governance: regression gate with committed baselines, dashboard, audit summary
- [x] M7a final: one-shot test-split run with pre-registered expectations
- [x] M8 provenance guard mode, mid-task injection suite, red-team sweep (null result)
- [x] Runtime/checkpoint confound: retracted claim corrected, same-checkpoint comparison, leak check in the gate
- [x] M9 MCP: server-side guarded tool server, suites over the protocol, host-side provenance, schema-presentation finding (docs/mcp.md)
- [ ] M7b CV and LinkedIn wording: on hold until Arda asks
- [ ] M4 router: deliberately not built

## Open, optional
- Run the original hybrid Qwen3-30B-A3B on Ollama (`qwen3:30b-a3b-q4_K_M`, 18.6 GB download) to separate reasoning from
  checkpoint; qwen3:8b check; API baseline (gpt-5-mini, key via `.env`); a successful injection to make the
  provenance guard measurable; spend the `agent_injection` test split once such an attack exists.

## Rules kept
Tune on validation only; test split is one-shot per configuration; compare model and runtime only after checking
checkpoint metadata; report scale (n) with every number.
