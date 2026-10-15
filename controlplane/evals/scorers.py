import json
import re
import unicodedata
from typing import Any

from jsonschema import Draft202012Validator

from controlplane.evals.contract import CaseOutcome, GoldenCase
from controlplane.types import ChatResult


def _norm(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return float(value)
    decomposed = unicodedata.normalize("NFKD", str(value).strip().casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _norm_amount(value: Any) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"[^0-9]", "", str(value))
    return digits or None


def _is_amount_field(name: str) -> bool:
    return name.endswith("_price") or name in {"total", "subtotal"}


def score_extraction(case: GoldenCase, result: ChatResult) -> CaseOutcome:
    base = {"case_id": case.id, "task": case.task}
    usage = {
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.usage.prompt_tokens,
        "completion_tokens": result.usage.completion_tokens,
    }
    try:
        parsed = json.loads(result.text)
    except json.JSONDecodeError:
        if result.finish_reason == "length":
            return CaseOutcome(
                **base,
                passed=False,
                failure="truncated",
                detail={
                    "output": result.text[:500],
                    "completion_tokens": usage["completion_tokens"],
                },
                **usage,
            )
        return CaseOutcome(
            **base,
            passed=False,
            failure="invalid_json",
            detail={"output": result.text[:500]},
            **usage,
        )
    if not isinstance(parsed, dict):
        return CaseOutcome(
            **base,
            passed=False,
            failure="invalid_json",
            detail={"output": result.text[:500]},
            **usage,
        )

    if case.response_schema is not None:
        errors = sorted(
            Draft202012Validator(case.response_schema).iter_errors(parsed), key=lambda e: e.path
        )
        if errors:
            return CaseOutcome(
                **base,
                passed=False,
                failure="schema_invalid",
                detail={"errors": [e.message for e in errors[:3]]},
                **usage,
            )

    field_results: dict[str, bool] = {}
    for name, expected in case.expected.items():
        actual = parsed.get(name)
        if _is_amount_field(name):
            field_results[name] = _norm_amount(actual) == _norm_amount(expected)
        else:
            field_results[name] = _norm(actual) == _norm(expected)
    passed = all(field_results.values())
    return CaseOutcome(
        **base,
        passed=passed,
        failure=None if passed else "wrong_value",
        detail={"fields": field_results, "actual": {k: parsed.get(k) for k in case.expected}},
        **usage,
    )


def score_tool_call(case: GoldenCase, result: ChatResult) -> CaseOutcome:
    base = {"case_id": case.id, "task": case.task}
    usage = {
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.usage.prompt_tokens,
        "completion_tokens": result.usage.completion_tokens,
    }

    def fail(category: str, **detail: Any) -> CaseOutcome:
        return CaseOutcome(**base, passed=False, failure=category, detail=detail, **usage)

    expected_tool = case.expected.get("tool")
    calls = result.tool_calls

    if expected_tool is None:
        if calls:
            return fail("unexpected_call", called=calls[0].name, call_count=len(calls))
        return CaseOutcome(**base, passed=True, **usage)

    if not calls:
        if result.finish_reason == "length":
            return fail("truncated", output=result.text[:300])
        return fail("no_call", output=result.text[:300])

    call = calls[0]
    tools_by_name = {t.name: t for t in case.tools}
    detail = {"called": call.name, "arguments": call.arguments, "call_count": len(calls)}
    if call.name not in tools_by_name:
        return fail("hallucinated_tool", **detail)
    if call.name != expected_tool:
        return fail("wrong_tool", expected=expected_tool, **detail)

    errors = list(
        Draft202012Validator(tools_by_name[call.name].parameters).iter_errors(call.arguments)
    )
    if errors:
        return fail("bad_args_schema", errors=[e.message for e in errors[:3]], **detail)

    expected_args = case.expected.get("arguments", {})
    mismatched = {
        k: {"expected": v, "actual": call.arguments.get(k)}
        for k, v in expected_args.items()
        if _norm(call.arguments.get(k)) != _norm(v)
    }
    if mismatched:
        return fail("wrong_args", mismatched=mismatched, **detail)
    return CaseOutcome(**base, passed=True, detail={"call_count": len(calls)}, **usage)


SCORERS = {"extraction": score_extraction, "tool_call": score_tool_call}
