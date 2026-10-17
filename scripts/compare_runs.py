"""Paired comparison of two configurations on the same cases (e.g. one model on two runtimes).

For every suite both configurations ran, reports pass counts, the cases where they disagree and an
exact two-sided sign test on the discordant pairs. With few cases the test has little power, so a
non-significant result means "cannot tell", not "equal".

Usage: python -m scripts.compare_runs --a mlx:Qwen3-30B-A3B-4bit --b ollama:qwen3_30b-a3b
       python -m scripts.compare_runs --a ollama:gemma4_26b --b ollama:gemma4_26b@mcp
"""

import argparse
import json
from math import comb
from pathlib import Path


def sign_test(only_a: int, only_b: int) -> float:
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def latest_runs(
    runs_dir: Path, runtime: str, model_key: str, max_tokens: int = 1024, transport: str = "direct"
) -> dict[tuple, Path]:
    found: dict[tuple, Path] = {}
    for run in sorted(runs_dir.iterdir()):
        report = run / "report.json"
        if not report.exists():
            continue
        meta = json.loads(report.read_text())["meta"]
        if (
            meta["runtime"] != runtime
            or meta["model"].split("/")[-1].replace(":", "_") != model_key
        ):
            continue
        if meta.get("split", "validation") != "validation":
            continue
        if meta.get("transport", "direct") != transport:
            continue
        if meta.get("max_tokens", 1024) != max_tokens:
            continue  # e.g. the deliberate max_tokens=40 regression demo is never comparable
        key = (
            meta["suite"],
            meta.get("guard_mode", "rules" if meta.get("guard") else "off"),
            meta.get("think"),
        )
        found[key] = run  # later runs overwrite earlier ones
    return found


def parse_spec(spec: str) -> tuple[str, str, str]:
    """`runtime:model_key[@transport]`; transport defaults to direct (ollama:gemma4_26b@mcp)."""
    head, _, transport = spec.partition("@")
    runtime, model_key = head.split(":", 1)
    return runtime, model_key, transport or "direct"


def outcomes(run: Path) -> dict[str, bool]:
    rows = [json.loads(line) for line in (run / "outcomes.jsonl").read_text().splitlines() if line]
    return {r["case_id"]: r["passed"] for r in rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, help="runtime:model_key")
    parser.add_argument("--b", required=True)
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    parser.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args()
    (rt_a, key_a, tr_a), (rt_b, key_b, tr_b) = parse_spec(args.a), parse_spec(args.b)
    runs_a, runs_b = (
        latest_runs(args.runs, rt_a, key_a, args.max_tokens, tr_a),
        latest_runs(args.runs, rt_b, key_b, args.max_tokens, tr_b),
    )
    for key in sorted(set(runs_a) & set(runs_b), key=str):
        a, b = outcomes(runs_a[key]), outcomes(runs_b[key])
        shared = sorted(set(a) & set(b))
        if len(shared) < len(a) or len(shared) < len(b):
            continue  # different case sets (a smoke run or an older golden set)
        only_a = [c for c in shared if a[c] and not b[c]]
        only_b = [c for c in shared if b[c] and not a[c]]
        suite, guard, think = key
        p_value = sign_test(len(only_a), len(only_b))
        print(
            f"{suite:17s} guard={guard:10s} A {sum(a.values())}/{len(a)}  "
            f"B {sum(b.values())}/{len(b)}  A-only {len(only_a)}  B-only {len(only_b)}  "
            f"sign-test p={p_value:.2f}"
        )
        if only_a or only_b:
            print(f"    A passes, B fails: {only_a}\n    B passes, A fails: {only_b}")


if __name__ == "__main__":
    main()
