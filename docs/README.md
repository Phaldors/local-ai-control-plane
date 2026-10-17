# Documentation index

Start with the top-level [README](../README.md). Everything below is dated 2026-10-15/16 and written in the order the
work happened; later documents correct earlier ones where noted.

| document | what it covers |
| --- | --- |
| [findings-m1.md](findings-m1.md) | Two runtimes, tracing, first golden suites; thinking budget dominates extraction |
| [findings-m2.md](findings-m2.md) | Three models, audited labels (golden v2), first router decision |
| [findings-m3.md](findings-m3.md) | Multi-receipt ladder (2 to 16 receipts); router revisited |
| [findings-m4.md](findings-m4.md) | Multi-step tool use (carries a correction note about the Qwen3 failures) |
| [findings-m5.md](findings-m5.md) | Security layer measured with the guard off and on |
| [findings-m6.md](findings-m6.md) | Regression gate, dashboard, audit; a deliberate-regression demo |
| [final-protocol.md](final-protocol.md) | The one-shot test-split protocol, written before the run |
| [final-report.md](final-report.md) | Final results, scorecard of the pre-registered expectations, addendum |
| [findings-injection.md](findings-injection.md) | Provenance guard, mid-task injection suite, red-team sweep (null result) |
| [findings-runtime-confound.md](findings-runtime-confound.md) | MLX vs Ollama, the retracted "same model" claim, same-checkpoint result, leak check |
| [same-checkpoint-plan.md](same-checkpoint-plan.md) | The plan for the same-checkpoint comparison, written before the runs |
| [mcp.md](mcp.md) | MCP server with server-side guard, running the suites over MCP, the schema-presentation finding, host-side provenance |
| [dashboard.html](dashboard.html) | One-page snapshot of the latest run per configuration (open in a browser) |
| `eval-reports/` | Archived reports and trajectories per stage (PII-redacted) |

Reading order for a short version: README, final-report, findings-m5, findings-runtime-confound.
