import json
import platform
import statistics
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from controlplane.client import LLMClient
from controlplane.evals.contract import CaseOutcome, GoldenCase
from controlplane.evals.scorers import SCORERS
from controlplane.tracing import TracedClient, TraceSink
from controlplane.types import ChatRequest, RuntimeError_


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(pct * (len(ordered) - 1)))
    return ordered[index]


def run_cases(
    client: LLMClient,
    model: str,
    cases: list[GoldenCase],
    max_tokens: int = 1024,
    think: bool | None = None,
) -> list[CaseOutcome]:
    outcomes = []
    for case in cases:
        request = ChatRequest(
            model=model,
            messages=case.messages,
            response_schema=case.response_schema,
            tools=case.tools,
            max_tokens=max_tokens,
            think=think,
        )
        try:
            result = client.chat(request)
        except RuntimeError_ as exc:
            outcomes.append(
                CaseOutcome(
                    case_id=case.id,
                    task=case.task,
                    passed=False,
                    failure="transport_error",
                    detail={"error": str(exc)},
                )
            )
            continue
        outcomes.append(SCORERS[case.task](case, result))
    return outcomes


def summarize(cases: list[GoldenCase], outcomes: list[CaseOutcome]) -> dict:
    by_task: dict[str, list[CaseOutcome]] = defaultdict(list)
    for outcome in outcomes:
        by_task[outcome.task].append(outcome)

    tasks = {}
    for task, items in by_task.items():
        failures: dict[str, list[str]] = defaultdict(list)
        for item in items:
            if item.failure:
                failures[item.failure].append(item.case_id)
        latencies = [i.latency_ms for i in items if i.latency_ms]
        summary = {
            "cases": len(items),
            "passed": sum(1 for i in items if i.passed),
            "pass_rate": sum(1 for i in items if i.passed) / len(items),
            "failures": {k: {"count": len(v), "case_ids": v} for k, v in sorted(failures.items())},
            "latency_ms_p50": _percentile(latencies, 0.5),
            "latency_ms_p95": _percentile(latencies, 0.95),
            "completion_tokens_mean": statistics.fmean(i.completion_tokens for i in items),
        }
        if task == "extraction":
            fields: dict[str, list[bool]] = defaultdict(list)
            for item in items:
                for name, ok in item.detail.get("fields", {}).items():
                    fields[name].append(ok)
            summary["json_valid_rate"] = sum(
                1
                for i in items
                if i.failure not in ("invalid_json", "truncated", "transport_error")
            ) / len(items)
            summary["schema_valid_rate"] = sum(
                1
                for i in items
                if i.failure
                not in ("invalid_json", "truncated", "schema_invalid", "transport_error")
            ) / len(items)
            summary["field_accuracy"] = {k: sum(v) / len(v) for k, v in fields.items()}
        tasks[task] = summary
    return tasks


def _ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0f} ms"


def render_markdown(meta: dict, tasks: dict) -> str:
    lines = [
        f"# Eval run {meta['run_id']}",
        "",
        f"- runtime: `{meta['runtime']}`, model: `{meta['model']}`",
        f"- suite: `{meta['suite']}` ({meta['case_count']} cases, split `{meta['split']}`)",
        f"- max_tokens: {meta['max_tokens']}, think: {meta['think']}",
        f"- commit: `{meta['commit']}`, host: {meta['host']}",
        "",
    ]
    for task, s in tasks.items():
        lines += [
            f"## {task}",
            "",
            f"- pass rate: **{s['passed']}/{s['cases']} ({s['pass_rate']:.0%})**",
            f"- latency p50/p95: {_ms(s['latency_ms_p50'])} / {_ms(s['latency_ms_p95'])}",
            f"- completion tokens (mean): {s['completion_tokens_mean']:.0f}",
        ]
        if task == "extraction":
            lines.append(
                f"- JSON valid: {s['json_valid_rate']:.0%}, "
                f"schema valid: {s['schema_valid_rate']:.0%}"
            )
            lines.append(f"- field accuracy: {s['field_accuracy']}")
        lines += ["", "### Failures (reported, never hidden)", ""]
        if not s["failures"]:
            lines.append("None.")
        for category, info in s["failures"].items():
            lines.append(f"- `{category}`: {info['count']} ({', '.join(info['case_ids'][:10])})")
        lines.append("")
    return "\n".join(lines)


def run_eval(
    client: LLMClient,
    model: str,
    cases: list[GoldenCase],
    suite: str,
    split: str,
    out_root: Path,
    max_tokens: int = 1024,
    think: bool | None = None,
) -> Path:
    run_id = (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + f"-{client.runtime}-{model.replace(':', '_').replace('/', '_')}"
    )
    run_dir = out_root / run_id
    traced = TracedClient(client, TraceSink(run_dir / "traces.jsonl"), run_id, tag=suite)

    outcomes = run_cases(traced, model, cases, max_tokens=max_tokens, think=think)
    tasks = summarize(cases, outcomes)
    meta = {
        "run_id": run_id,
        "runtime": client.runtime,
        "model": model,
        "suite": suite,
        "split": split,
        "max_tokens": max_tokens,
        "think": think,
        "case_count": len(cases),
        "commit": _git_commit(),
        "host": f"{platform.machine()} / {platform.platform()}",
    }
    (run_dir / "outcomes.jsonl").write_text(
        "\n".join(o.model_dump_json() for o in outcomes) + "\n", encoding="utf-8"
    )
    (run_dir / "report.json").write_text(
        json.dumps({"meta": meta, "tasks": tasks}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "report.md").write_text(render_markdown(meta, tasks), encoding="utf-8")
    return run_dir
