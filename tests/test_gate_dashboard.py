import copy
import json
from pathlib import Path

from controlplane.cli import run_gate
from controlplane.dashboard import build_dashboard, load_latest_runs, render
from controlplane.gate import baseline_key, evaluate, find_baseline


def make_report(
    passed=20, cases=21, failures=None, guard=False, p50=1000.0, security=None, tokens=50.0
):
    task = {
        "cases": cases,
        "passed": passed,
        "pass_rate": passed / cases,
        "failures": {k: {"count": v, "case_ids": []} for k, v in (failures or {}).items()},
        "latency_ms_p50": p50,
        "latency_ms_p95": p50 * 2,
        "completion_tokens_mean": tokens,
    }
    if security is not None:
        task["security"] = security
    return {
        "meta": {
            "run_id": "r",
            "runtime": "ollama",
            "model": "gemma4:26b",
            "suite": "agent_security",
            "think": False,
            "max_tokens": 1024,
            "guard": guard,
            "case_count": cases,
        },
        "tasks": {"agent": task},
    }


CLEAN = {
    "attempted_violations": 4,
    "executed_violations": 0,
    "leaks": 0,
    "blocked_calls": 4,
    "escalated_calls": 1,
}


def statuses(result):
    return {c.name: c.status for c in result.checks}


def test_identical_run_passes():
    base = make_report(security=CLEAN, guard=True)
    result = evaluate(copy.deepcopy(base), base)
    assert result.status == "PASS"


def test_pass_rate_drop_beyond_tolerance_fails_but_within_tolerance_passes():
    base = make_report(passed=20)
    assert evaluate(make_report(passed=18), base).status == "PASS"
    result = evaluate(make_report(passed=17), base)
    assert result.status == "FAIL" and statuses(result)["agent.pass_rate"] == "fail"


def test_truncation_growth_and_severe_failures_fail_new_minor_ones_only_warn():
    base = make_report(failures={"truncated": 1})
    assert evaluate(make_report(failures={"truncated": 3}), base).status == "FAIL"
    assert (
        evaluate(make_report(failures={"truncated": 1, "forbidden_call": 1}), base).status == "FAIL"
    )
    assert (
        evaluate(make_report(failures={"truncated": 1, "wrong_answer": 1}), base).status == "WARN"
    )


def test_guard_invariant_fails_even_when_baseline_was_equally_bad():
    bad = {**CLEAN, "executed_violations": 2}
    base = make_report(security=bad, guard=True)
    result = evaluate(copy.deepcopy(base), base)
    assert result.status == "FAIL" and statuses(result)["agent.invariant"] == "fail"


def test_guard_invariant_is_not_applied_with_the_guard_off():
    bad = {**CLEAN, "executed_violations": 5, "leaks": 3}
    base = make_report(security=bad, guard=False)
    assert "agent.invariant" not in statuses(evaluate(copy.deepcopy(base), base))


def test_latency_regression_fails():
    base = make_report(p50=1000.0)
    assert evaluate(make_report(p50=1600.0), base).status == "PASS"
    assert evaluate(make_report(p50=2000.0), base).status == "FAIL"


def test_changed_case_count_demands_an_explicit_rebaseline():
    result = evaluate(make_report(cases=25, passed=25), make_report(cases=21))
    assert statuses(result) == {"agent.golden_set": "fail"}


def test_token_growth_warns():
    assert evaluate(make_report(tokens=200.0), make_report(tokens=50.0)).status == "WARN"


def test_baseline_key_and_lookup(tmp_path):
    report = make_report()
    key = baseline_key(report["meta"])
    assert key == "ollama__gemma4_26b__agent_security__think-off__guard-off"
    assert find_baseline(tmp_path, report["meta"]) is None
    (tmp_path / f"{key}.json").write_text("{}")
    assert find_baseline(tmp_path, report["meta"]) == tmp_path / f"{key}.json"


def test_run_gate_exit_codes(tmp_path):
    base_dir, run_dir = tmp_path / "baselines", tmp_path / "run"
    base_dir.mkdir()
    run_dir.mkdir()
    (run_dir / "report.json").write_text(json.dumps(make_report(passed=20)))
    assert run_gate([run_dir], base_dir, 2) == 2  # no baseline yet
    key = baseline_key(make_report()["meta"])
    (base_dir / f"{key}.json").write_text(json.dumps(make_report(passed=20)))
    assert run_gate([run_dir], base_dir, 2) == 0
    (run_dir / "report.json").write_text(json.dumps(make_report(passed=10)))
    assert run_gate([run_dir], base_dir, 2) == 1


def write_run(root: Path, name: str, report: dict, traces=(), audit=()):
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "report.json").write_text(json.dumps(report))
    (directory / "traces.jsonl").write_text("\n".join(json.dumps(t) for t in traces))
    (directory / "audit.jsonl").write_text("\n".join(json.dumps(a) for a in audit))


def test_dashboard_keeps_latest_run_per_configuration(tmp_path):
    write_run(tmp_path, "20261001T000000Z-a", make_report(passed=5))
    write_run(tmp_path, "20261002T000000Z-a", make_report(passed=19))
    runs = load_latest_runs(tmp_path)
    assert len(runs) == 1 and runs[0]["tasks"]["agent"]["passed"] == 19


def test_dashboard_never_embeds_prompts_and_escapes_html(tmp_path):
    report = make_report(security=CLEAN, guard=True)
    report["meta"]["model"] = "evil<img onerror=x>"
    traces = [
        {
            "status": "ok",
            "latency_ms": 100.0,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "generation_tps": 50.0,
            "messages": [{"content": "SECRET-PROMPT"}],
            "output": "SECRET-OUT",
        }
    ]
    audit = [{"decision": "block", "rule": "cross_customer_access", "tool": "get_order"}]
    write_run(tmp_path, "20261001T000000Z-a", report, traces, audit)
    out = build_dashboard(tmp_path, tmp_path / "dash.html").read_text()
    assert "SECRET-PROMPT" not in out and "SECRET-OUT" not in out
    assert "<img onerror=x>" not in out and "&lt;img onerror=x&gt;" in out
    assert "cross_customer_access" in out and "100 ms" in out


def test_render_handles_no_runs():
    assert "No security runs" in render([])


def test_lowering_max_tokens_is_caught_against_the_same_baseline():
    base = make_report()
    lowered = make_report()
    lowered["meta"]["max_tokens"] = 40
    assert baseline_key(lowered["meta"]) == baseline_key(base["meta"])
    result = evaluate(lowered, base)
    assert result.status == "FAIL" and statuses(result)["config.max_tokens"] == "fail"


def test_dashboard_separates_runs_that_differ_only_in_max_tokens(tmp_path):
    write_run(tmp_path, "20261001T000000Z-a", make_report(passed=19))
    low = make_report(passed=5)
    low["meta"]["max_tokens"] = 40
    write_run(tmp_path, "20261002T000000Z-a", low)
    runs = load_latest_runs(tmp_path)
    assert sorted(r["tasks"]["agent"]["passed"] for r in runs) == [5, 19]
    assert "max 40" in render(runs)


def test_dashboard_hides_smoke_runs_and_older_smaller_golden_sets(tmp_path):
    write_run(tmp_path, "20261001T000000Z-a", make_report(passed=4, cases=5))
    write_run(tmp_path, "20261002T000000Z-a", make_report(passed=19, cases=21))
    runs = load_latest_runs(tmp_path)
    assert [r["tasks"]["agent"]["cases"] for r in runs] == [21]
