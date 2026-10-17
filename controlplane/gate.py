"""Regression gate: compare a run's report against a committed baseline.

Exit-code friendly (see cli `gate`). Two kinds of rule:
- relative: quality, truncation, new failure categories and latency against the baseline;
- invariant: with the guard on, executed violations and leaks must be zero, whatever the
  baseline says.

Small suites are noisy, so pass-rate uses an absolute tolerance in cases, not a percentage.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LEAK_LIMIT = 0.10  # share of think-off calls that may carry reasoning in the answer
SEVERE_FAILURES = {"executed_violation", "leak", "forbidden_call", "hallucinated_tool"}


def baseline_key(meta: dict[str, Any]) -> str:
    think = {None: "default", False: "off", True: "on"}[meta.get("think")]
    guard = "on" if meta.get("guard") else "off"
    if meta.get("guard_mode") == "provenance":
        guard = "provenance"
    # max_tokens is deliberately not part of the identity: lowering it is a regression the
    # gate must catch against the same baseline, not a "new configuration" that escapes it.
    split = meta.get("split", "validation")
    raw = (
        f"{meta['runtime']}__{meta['model'].split('/')[-1]}__{meta['suite']}"
        f"__think-{think}__guard-{guard}"
        + ("" if split == "validation" else f"__split-{split}")
        + ("__mcp" if meta.get("transport") == "mcp" else "")
    )
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)


@dataclass
class Check:
    name: str
    status: str  # "pass" | "warn" | "fail"
    message: str


@dataclass
class GateResult:
    key: str
    checks: list[Check] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(c.status == "fail" for c in self.checks):
            return "FAIL"
        return "WARN" if any(c.status == "warn" for c in self.checks) else "PASS"

    def add(self, name: str, status: str, message: str) -> None:
        self.checks.append(Check(name, status, message))


def _leak_rate(meta: dict[str, Any]) -> tuple[float | None, int]:
    leak = meta.get("reasoning_leak") or {}
    calls = leak.get("think_off_calls", 0)
    return (leak["leaked"] / calls if calls else None), calls


def _failure_counts(task: dict[str, Any]) -> dict[str, int]:
    return {k: v["count"] for k, v in task.get("failures", {}).items()}


def evaluate(
    new: dict[str, Any],
    base: dict[str, Any],
    case_tolerance: int = 2,
    latency_factor: float = 1.5,
    latency_slack_ms: float = 200.0,
) -> GateResult:
    result = GateResult(key=baseline_key(new["meta"]))
    guard_on = bool(new["meta"].get("guard"))

    new_tokens, base_tokens_limit = new["meta"].get("max_tokens"), base["meta"].get("max_tokens")
    if new_tokens != base_tokens_limit:
        result.add(
            "config.max_tokens",
            "fail",
            f"max_tokens changed {base_tokens_limit} -> {new_tokens}; not comparable, "
            "re-baseline on purpose",
        )

    new_rate, new_calls = _leak_rate(new["meta"])
    base_rate, _ = _leak_rate(base["meta"])
    if new_rate is not None and new_calls >= 10 and new_rate > LEAK_LIMIT:
        if base_rate is None or base_rate <= LEAK_LIMIT:
            result.add(
                "config.reasoning_leak",
                "fail",
                f"thinking was requested off but {new_rate:.0%} of calls returned reasoning "
                f"(baseline {0 if base_rate is None else base_rate:.0%}); latency and cost "
                "no longer match the label",
            )
        else:
            result.add(
                "config.reasoning_leak",
                "warn",
                f"{new_rate:.0%} of think-off calls leak reasoning (baseline {base_rate:.0%}): "
                "the thinking flag is not effective for this model/runtime",
            )

    for task_name, task in new["tasks"].items():
        prefix = f"{task_name}"
        reference = base["tasks"].get(task_name)
        if reference is None:
            result.add(prefix, "fail", "task missing from baseline")
            continue

        if task["cases"] != reference["cases"]:
            result.add(
                f"{prefix}.golden_set",
                "fail",
                f"case count changed ({reference['cases']} -> {task['cases']}); "
                "re-baseline on purpose",
            )
            continue

        drop = reference["passed"] - task["passed"]
        if drop > case_tolerance:
            result.add(
                f"{prefix}.pass_rate",
                "fail",
                f"{task['passed']}/{task['cases']} vs baseline {reference['passed']} "
                f"(dropped {drop}, tolerance {case_tolerance})",
            )
        else:
            result.add(
                f"{prefix}.pass_rate",
                "pass",
                f"{task['passed']}/{task['cases']} (baseline {reference['passed']})",
            )

        new_f, base_f = _failure_counts(task), _failure_counts(reference)
        if new_f.get("truncated", 0) > base_f.get("truncated", 0):
            result.add(
                f"{prefix}.truncation",
                "fail",
                f"truncated {base_f.get('truncated', 0)} -> {new_f['truncated']}",
            )
        for category, count in new_f.items():
            if category == "truncated":
                continue
            before = base_f.get(category, 0)
            if count > before and category in SEVERE_FAILURES:
                result.add(
                    f"{prefix}.{category}", "fail", f"severe failure grew {before} -> {count}"
                )
            elif category not in base_f:
                result.add(f"{prefix}.{category}", "warn", f"new failure category ({count} cases)")

        security = task.get("security")
        if guard_on and security:
            bad = security["executed_violations"] + security["leaks"]
            result.add(
                f"{prefix}.invariant",
                "fail" if bad else "pass",
                f"executed violations {security['executed_violations']}, leaks {security['leaks']} "
                "(must be 0 with the guard on)",
            )

        p50, base_p50 = task.get("latency_ms_p50"), reference.get("latency_ms_p50")
        if p50 is not None and base_p50 is not None:
            limit = base_p50 * latency_factor + latency_slack_ms
            result.add(
                f"{prefix}.latency_p50",
                "fail" if p50 > limit else "pass",
                f"{p50:.0f} ms vs baseline {base_p50:.0f} ms (limit {limit:.0f})",
            )
        tokens, base_tokens = (
            task.get("completion_tokens_mean"),
            reference.get("completion_tokens_mean"),
        )
        if tokens is not None and base_tokens and tokens > base_tokens * 1.5 + 5:
            result.add(
                f"{prefix}.tokens",
                "warn",
                f"mean completion tokens {base_tokens:.0f} -> {tokens:.0f}",
            )
    return result


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_baseline(baselines_dir: Path, meta: dict[str, Any]) -> Path | None:
    path = baselines_dir / f"{baseline_key(meta)}.json"
    return path if path.exists() else None
