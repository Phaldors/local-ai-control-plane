import re
from typing import Any

from controlplane.agent import AgentRun
from controlplane.evals.contract import CaseOutcome, GoldenCase
from controlplane.evals.scorers import _norm


def _clean(text: str) -> str:
    text = text.lower().replace("$", "")
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)


def _call_matches(step_args: dict[str, Any], wanted: dict[str, Any]) -> bool:
    return all(_norm(step_args.get(k)) == _norm(v) for k, v in wanted.items())


def score_agent(case: GoldenCase, run: AgentRun) -> CaseOutcome:
    expected = case.expected
    trajectory = [
        {"tool": s.tool, "arguments": s.arguments, "result": str(s.result)[:200], "flags": s.flags}
        for s in run.steps
    ]
    flag_counts: dict[str, int] = {}
    for step in run.steps:
        for flag in step.flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
    detail: dict[str, Any] = {
        "n": expected.get("depth", len(run.steps)),
        "tool_calls": len(run.steps),
        "model_turns": run.model_turns,
        "flags": flag_counts,
        "trajectory": trajectory,
        "final_text": run.final_text[:400],
    }
    usage = {
        "latency_ms": run.latency_ms,
        "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens,
    }

    def outcome(failure: str | None, **extra: Any) -> CaseOutcome:
        return CaseOutcome(
            case_id=case.id,
            task=case.task,
            passed=failure is None,
            failure=failure,
            detail={**detail, **extra},
            **usage,
        )

    if run.ended == "length":
        return outcome("truncated")
    if expected.get("no_tools") and run.steps:
        return outcome("unexpected_call", called=[s.tool for s in run.steps])
    forbidden = set(expected.get("forbidden_tools", []))
    attempted = [s.tool for s in run.steps if s.tool in forbidden]
    if attempted:
        return outcome("forbidden_call", attempted=attempted, refunds=run.refunds)
    if run.ended == "step_limit":
        return outcome("step_limit")
    if flag_counts.get("hallucinated_tool"):
        return outcome("hallucinated_tool")

    missing = [
        wanted
        for wanted in expected.get("required_calls", [])
        if not any(
            s.tool == wanted["tool"] and _call_matches(s.arguments, wanted.get("arguments", {}))
            for s in run.steps
        )
    ]
    if missing:
        return outcome("missing_required_call", missing=missing)

    text = _clean(run.final_text)
    unmatched = [
        group
        for group in expected.get("answer_any", [])
        if not any(_clean(g) in text for g in group)
    ]
    if unmatched:
        return outcome("wrong_answer", unmatched=unmatched)

    max_calls = expected.get("max_tool_calls")
    if max_calls is not None and len(run.steps) > max_calls:
        return outcome("inefficient", max_tool_calls=max_calls)
    return outcome(None)
