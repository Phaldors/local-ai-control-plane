import json
import platform
import statistics
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from controlplane.agent import run_agent
from controlplane.audit import AuditLog
from controlplane.client import LLMClient
from controlplane.evals.agent_scorer import score_agent
from controlplane.evals.contract import CaseOutcome, GoldenCase
from controlplane.evals.scorers import SCORERS
from controlplane.guard import GuardedWorld, PolicyGuard
from controlplane.mcp_client import McpWorld
from controlplane.memory import runtime_memory_mb
from controlplane.redaction import redact_obj
from controlplane.tracing import TracedClient, TraceSink
from controlplane.types import ChatRequest, RuntimeError_
from controlplane.worlds.shop import ShopWorld


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


def guard_mode(guard: bool | str) -> str:
    """Accepts the old boolean as well: True means the rule-based guard."""
    if guard is True:
        return "rules"
    return "off" if guard is False else guard


def make_world(
    case: GoldenCase,
    guard: bool | str,
    audit: AuditLog | None = None,
    transport: str = "direct",
) -> ShopWorld | GuardedWorld | McpWorld:
    world: ShopWorld | GuardedWorld = ShopWorld()
    mode = guard_mode(guard)
    if transport == "mcp" and mode == "provenance":
        raise ValueError(
            "provenance needs the user's messages, which an MCP server never sees: it cannot be "
            "enforced behind MCP (use --transport direct)"
        )
    if mode != "off":
        world = GuardedWorld(
            world,
            PolicyGuard(
                auth_customer_id=case.expected.get("auth_customer"),
                provenance=mode == "provenance",
            ),
            audit=audit,
            case_id=case.id,
        )
    return McpWorld(world) if transport == "mcp" else world


def run_cases(
    client: LLMClient,
    model: str,
    cases: list[GoldenCase],
    max_tokens: int = 1024,
    think: bool | None = None,
    guard: bool | str = False,
    audit: AuditLog | None = None,
    transport: str = "direct",
) -> list[CaseOutcome]:
    outcomes = []
    for case in cases:
        if case.task == "agent":
            world = make_world(case, guard, audit, transport)
            try:
                run = run_agent(
                    client,
                    model,
                    case.messages,
                    world,
                    max_turns=case.expected.get("max_turns", 10),
                    max_tokens=max_tokens,
                    think=think,
                )
                if hasattr(world, "close"):
                    world.close()
            except RuntimeError_ as exc:
                if hasattr(world, "close"):
                    world.close()
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
            outcomes.append(score_agent(case, run))
            continue
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
            "prompt_tokens_total": sum(i.prompt_tokens for i in items),
            "completion_tokens_total": sum(i.completion_tokens for i in items),
            "latency_ms_total": sum(i.latency_ms for i in items),
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
        if task == "agent":
            by_depth: dict[int, list[CaseOutcome]] = defaultdict(list)
            for item in items:
                by_depth[item.detail.get("n", 0)].append(item)
            summary["by_depth"] = {
                str(n): {
                    "cases": len(group),
                    "pass_rate": sum(1 for g in group if g.passed) / len(group),
                }
                for n, group in sorted(by_depth.items())
            }
            summary["tool_calls_mean"] = statistics.fmean(
                i.detail.get("tool_calls", 0) for i in items
            )
            sec = [i.detail.get("security", {}) for i in items]
            summary["security"] = {
                "attempted_violations": sum(len(x.get("attempted", [])) for x in sec),
                "executed_violations": sum(len(x.get("executed", [])) for x in sec),
                "leaks": sum(len(x.get("leaks", [])) for x in sec),
                "blocked_calls": sum(x.get("blocked", 0) for x in sec),
                "escalated_calls": sum(x.get("escalated", 0) for x in sec),
            }
            summary["recovered_tool_errors"] = sum(
                1 for i in items if i.passed and i.detail.get("flags", {}).get("tool_error")
            )
        if task == "multi_extraction":
            by_n: dict[int, list[CaseOutcome]] = defaultdict(list)
            for item in items:
                if "n" in item.detail:
                    by_n[item.detail["n"]].append(item)
            summary["by_receipt_count"] = {
                str(n): {
                    "cases": len(group),
                    "pass_rate": sum(1 for g in group if g.passed) / len(group),
                    "item_accuracy": statistics.fmean(g.detail["item_accuracy"] for g in group),
                }
                for n, group in sorted(by_n.items())
            }
        tasks[task] = summary
    return tasks


def _leak_line(meta: dict) -> str:
    leak = meta.get("reasoning_leak") or {}
    calls = leak.get("think_off_calls", 0)
    if not calls:
        return "reasoning leak: n/a (thinking not requested off)"
    return (
        f"reasoning leak: {leak['leaked']}/{calls} think-off calls "
        f"({leak['leaked'] / calls:.0%}) returned reasoning in the answer"
    )


def _mb(value: float | None) -> str:
    return "n/a" if value is None else f"{value / 1024:.1f} GB"


def _ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0f} ms"


def render_markdown(meta: dict, tasks: dict) -> str:
    lines = [
        f"# Eval run {meta['run_id']}",
        "",
        f"- runtime: `{meta['runtime']}`, model: `{meta['model']}`",
        f"- suite: `{meta['suite']}` ({meta['case_count']} cases, split `{meta['split']}`)",
        f"- max_tokens: {meta['max_tokens']}, think: {meta['think']}, "
        f"guard: {meta.get('guard_mode', meta['guard'])}",
        f"- resident model memory (approx): {_mb(meta['model_memory_mb'])}",
        f"- {_leak_line(meta)}",
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
        if task == "agent":
            lines.append(
                f"- mean tool calls: {s['tool_calls_mean']:.1f}, "
                f"passed after recovering from a tool error: {s['recovered_tool_errors']}"
            )
            sec = s["security"]
            lines.append(
                f"- security: attempted violations {sec['attempted_violations']}, "
                f"executed {sec['executed_violations']}, leaks {sec['leaks']}, "
                f"blocked calls {sec['blocked_calls']}, escalated {sec['escalated_calls']}"
            )
            for n, info in s["by_depth"].items():
                lines.append(f"- depth {n}: pass {info['pass_rate']:.0%} ({info['cases']} cases)")
        if task == "multi_extraction":
            for n, info in s["by_receipt_count"].items():
                lines.append(
                    f"- {n} receipts: pass {info['pass_rate']:.0%}, "
                    f"per-receipt accuracy {info['item_accuracy']:.0%} ({info['cases']} cases)"
                )
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
    guard: bool | str = False,
    transport: str = "direct",
) -> Path:
    run_id = (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + f"-{client.runtime}-{model.replace(':', '_').replace('/', '_')}"
    )
    run_dir = out_root / run_id
    traced = TracedClient(client, TraceSink(run_dir / "traces.jsonl"), run_id, tag=suite)

    audit = AuditLog(run_dir / "audit.jsonl") if guard_mode(guard) != "off" else None
    outcomes = run_cases(
        traced,
        model,
        cases,
        max_tokens=max_tokens,
        think=think,
        guard=guard,
        audit=audit,
        transport=transport,
    )
    tasks = summarize(cases, outcomes)
    meta = {
        "run_id": run_id,
        "runtime": client.runtime,
        "model": model,
        "suite": suite,
        "split": split,
        "max_tokens": max_tokens,
        "think": think,
        "guard": guard_mode(guard) != "off",
        "guard_mode": guard_mode(guard),
        "transport": transport,
        "case_count": len(cases),
        "model_memory_mb": runtime_memory_mb(client.runtime, model),
        "reasoning_leak": {
            "think_off_calls": traced.think_off_calls,
            "leaked": traced.leaked_calls,
        },
        "commit": _git_commit(),
        "host": f"{platform.machine()} / {platform.platform()}",
    }
    (run_dir / "outcomes.jsonl").write_text(
        "\n".join(json.dumps(redact_obj(o.model_dump()), ensure_ascii=False) for o in outcomes)
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "report.json").write_text(
        json.dumps({"meta": meta, "tasks": tasks}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "report.md").write_text(render_markdown(meta, tasks), encoding="utf-8")
    return run_dir
