"""One self-contained HTML page (no JS, no external assets) built from run directories.

Shows the latest run per configuration: quality, latency and tokens from the traces, the
security comparison, failure taxonomy and the audit summary. Prompts and outputs are never
embedded: only counts and timings, so the page is safe to commit.
"""

import json
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from controlplane.gate import baseline_key
from controlplane.reasoning import looks_like_leaked_reasoning


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def trace_stats(run_dir: Path, think_off: bool = False) -> dict[str, Any]:
    rows = _read_jsonl(run_dir / "traces.jsonl")
    ok = [r for r in rows if r.get("status") == "ok"]
    latencies = [r["latency_ms"] for r in ok]
    tps = [r["generation_tps"] for r in ok if r.get("generation_tps")]
    return {
        "calls": len(rows),
        "errors": len(rows) - len(ok),
        "p50": _pct(latencies, 0.5),
        "p95": _pct(latencies, 0.95),
        "prompt_tokens": sum(r.get("prompt_tokens", 0) for r in ok),
        "completion_tokens": sum(r.get("completion_tokens", 0) for r in ok),
        "tps": statistics.median(tps) if tps else None,
        # share of calls with reasoning in the answer; only meaningful when thinking was off
        "leak": (
            sum(looks_like_leaked_reasoning(r.get("output") or "") for r in ok) / len(ok)
            if think_off and ok
            else None
        ),
    }


def load_latest_runs(runs_dir: Path) -> list[dict[str, Any]]:
    """Latest run per (runtime, model, suite, think, guard, max_tokens)."""
    latest: dict[str, dict[str, Any]] = {}
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        report = run_dir / "report.json"
        if not report.exists():
            continue
        data = json.loads(report.read_text(encoding="utf-8"))
        data["meta"].setdefault("max_tokens", 1024)  # reports written before these keys existed
        data["meta"].setdefault("guard", False)
        data["dir"] = run_dir
        data["traces"] = trace_stats(run_dir, think_off=data["meta"].get("think") is False)
        data["audit"] = _read_jsonl(run_dir / "audit.jsonl")
        key = f"{baseline_key(data['meta'])}__max{data['meta'].get('max_tokens')}"
        latest[key] = data  # sorted by timestamp: later overwrites

    # Hide smoke runs (--limit) and runs on an older, smaller golden set: only runs that cover
    # the largest case count seen for their suite and split are comparable.
    def group(run: dict[str, Any]) -> tuple[str, str]:
        return run["meta"]["suite"], run["meta"].get("split", "validation")

    biggest: dict[tuple[str, str], int] = defaultdict(int)
    for run in latest.values():
        biggest[group(run)] = max(biggest[group(run)], run["meta"]["case_count"])
    kept = [r for r in latest.values() if r["meta"]["case_count"] == biggest[group(r)]]
    return sorted(kept, key=lambda d: (d["meta"]["model"], d["meta"]["suite"]))


def _config_label(meta: dict[str, Any]) -> str:
    think = {None: "think default", False: "think off", True: "think on"}[meta.get("think")]
    guard = ", guard on" if meta.get("guard") else ""
    if meta.get("guard_mode") == "provenance":
        guard = ", guard+provenance"
    limit = meta.get("max_tokens", 1024)
    cap = f", max {limit}" if limit != 1024 else ""
    if meta.get("split", "validation") != "validation":
        cap += f", {meta['split']} split"
    if meta.get("transport") == "mcp":
        cap += ", via MCP"
    return f"{meta['model'].split('/')[-1]} · {meta['runtime']} · {think}{cap}{guard}"


def _fmt_ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.0f} ms"


def _bar(rate: float) -> str:
    return f'<span class="bar"><i style="width:{rate * 100:.0f}%"></i></span>'


def _table(headers: list[str], rows: list[list[str]], numeric_from: int = 1) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = "".join(
            f'<td class="{"n" if i >= numeric_from else ""}">{cell}</td>'
            for i, cell in enumerate(row)
        )
        body += f"<tr>{cells}</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render(runs: list[dict[str, Any]]) -> str:
    quality, perf, security, failures = [], [], [], []
    for run in runs:
        meta, task = run["meta"], next(iter(run["tasks"].values()))
        label = escape(_config_label(meta))
        suite = escape(meta["suite"])
        quality.append(
            [
                label,
                suite,
                f"{task['passed']}/{task['cases']} {_bar(task['pass_rate'])}",
                f"{task['pass_rate']:.0%}",
            ]
        )
        stats = run["traces"]
        perf.append(
            [
                label,
                suite,
                str(stats["calls"]),
                _fmt_ms(stats["p50"]),
                _fmt_ms(stats["p95"]),
                f"{stats['prompt_tokens']:,}",
                f"{stats['completion_tokens']:,}",
                "n/a" if stats["tps"] is None else f"{stats['tps']:.0f}",
                "n/a"
                if not meta.get("model_memory_mb")
                else f"{meta['model_memory_mb'] / 1024:.1f} GB",
                "-" if stats["leak"] is None else f"{stats['leak']:.0%}",
            ]
        )
        sec = task.get("security")
        if sec and (
            meta["suite"] == "agent_security" or sec["attempted_violations"] or sec["blocked_calls"]
        ):
            security.append(
                [
                    label,
                    suite,
                    "on" if meta.get("guard") else "off",
                    f"{task['passed']}/{task['cases']}",
                    str(sec["attempted_violations"]),
                    f"<b>{sec['executed_violations']}</b>",
                    f"<b>{sec['leaks']}</b>",
                    str(sec["blocked_calls"]),
                    str(sec["escalated_calls"]),
                ]
            )
        for category, info in task.get("failures", {}).items():
            failures.append([label, suite, escape(category), str(info["count"])])

    decisions: Counter[tuple[str, str, str]] = Counter()
    for run in runs:
        for event in run["audit"]:
            decisions[(event["decision"], event["rule"], event["tool"])] += 1
    audit_rows = [
        [escape(d), escape(r), escape(t), str(n)] for (d, r, t), n in sorted(decisions.items())
    ]

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    sections = [
        (
            "Quality (pass rate per suite)",
            _table(["configuration", "suite", "passed", "rate"], quality, 2),
        ),
        (
            "Latency and tokens (from traces)",
            _table(
                [
                    "configuration",
                    "suite",
                    "calls",
                    "p50",
                    "p95",
                    "prompt tok",
                    "completion tok",
                    "tok/s",
                    "RSS",
                    "leak",
                ],
                perf,
                2,
            ),
        ),
        (
            "Security: attempted vs executed",
            _table(
                [
                    "configuration",
                    "suite",
                    "guard",
                    "passed",
                    "attempted",
                    "executed",
                    "leaks",
                    "blocked",
                    "escalated",
                ],
                security,
                2,
            )
            if security
            else "<p>No security runs.</p>",
        ),
        (
            "Failure taxonomy (never hidden)",
            _table(["configuration", "suite", "category", "cases"], failures, 3)
            if failures
            else "<p>No failures.</p>",
        ),
        (
            "Audit trail summary (guard decisions)",
            _table(["decision", "rule", "tool", "events"], audit_rows, 3)
            if audit_rows
            else "<p>No audited runs yet.</p>",
        ),
    ]
    body = "".join(f"<section><h2>{escape(title)}</h2>{html}</section>" for title, html in sections)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Local AI Control Plane</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#ddd;--bar:#2b6cb0;--card:#f7f7f7}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151515;--fg:#eee;--mut:#9a9a9a;--line:#333;--bar:#63a4e8;--card:#1e1e1e}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:16px}}
h1{{font-size:1.4rem;margin:.2em 0}} h2{{font-size:1.05rem;margin:1.6em 0 .5em}}
.sub{{color:var(--mut);margin:0 0 1em}}
section{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
th{{color:var(--mut);font-weight:600}} td.n{{font-variant-numeric:tabular-nums}}
.bar{{display:inline-block;width:70px;height:8px;background:var(--card);border:1px solid var(--line);border-radius:4px;vertical-align:middle;margin-left:6px}}
.bar i{{display:block;height:100%;background:var(--bar);border-radius:3px}}
footer{{color:var(--mut);margin-top:2em;font-size:.85rem}}
</style></head><body>
<h1>Local AI Control Plane</h1>
<p class="sub">Latest run per configuration. Generated {generated}. Single runs on small suites (n=21 to 50);
differences of one or two cases are noise. No prompts or outputs are embedded.</p>
{body}
<footer>Source: run directories (report.json, traces.jsonl, audit.jsonl).</footer>
</body></html>"""


def build_dashboard(runs_dir: Path, out_path: Path) -> Path:
    runs = load_latest_runs(runs_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(runs), encoding="utf-8")
    return out_path
