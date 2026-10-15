import argparse
import shutil
from pathlib import Path

from controlplane.client import LLMClient
from controlplane.dashboard import build_dashboard
from controlplane.evals.contract import load_cases
from controlplane.evals.runner import run_eval
from controlplane.gate import baseline_key, evaluate, find_baseline, load_report
from controlplane.runtimes.mlx import MLXClient
from controlplane.runtimes.ollama import OllamaClient

SUITES = {
    "extraction": Path("golden/extraction.jsonl"),
    "tool_call": Path("golden/tool_call.jsonl"),
    "multi_extraction": Path("golden/multi_extraction.jsonl"),
    "agent": Path("golden/agent.jsonl"),
    "agent_security": Path("golden/agent_security.jsonl"),
}


def build_client(runtime: str, base_url: str | None) -> LLMClient:
    if runtime == "ollama":
        return OllamaClient(base_url=base_url or "http://localhost:11434")
    if runtime == "mlx":
        return MLXClient(base_url=base_url or "http://localhost:8080")
    raise SystemExit(f"unknown runtime: {runtime}")


def test_run_exists(
    runs: Path,
    runtime: str,
    model: str,
    suite: str,
    think: bool | None,
    guard: bool,
    max_tokens: int,
) -> Path | None:
    """The earlier test-split run of exactly this configuration, if any."""
    if not runs.exists():
        return None
    for report in sorted(runs.glob("*/report.json")):
        meta = load_report(report)["meta"]
        if (
            meta.get("split") == "test"
            and meta["runtime"] == runtime
            and meta["model"] == model
            and meta["suite"] == suite
            and meta.get("think") == think
            and bool(meta.get("guard")) == guard
            and meta.get("max_tokens", 1024) == max_tokens
        ):
            return report.parent
    return None


def _report_path(path: Path) -> Path:
    return path / "report.json" if path.is_dir() else path


def run_gate(reports: list[Path], baselines: Path, tolerance: int) -> int:
    """0 = all PASS/WARN, 1 = at least one FAIL, 2 = a baseline is missing."""
    code = 0
    for path in map(_report_path, reports):
        new = load_report(path)
        baseline_path = find_baseline(baselines, new["meta"])
        if baseline_path is None:
            print(f"NO BASELINE  {baseline_key(new['meta'])}  (run baseline-save first)")
            code = max(code, 2)
            continue
        result = evaluate(new, load_report(baseline_path), case_tolerance=tolerance)
        print(f"{result.status}  {result.key}")
        for check in result.checks:
            if check.status != "pass":
                print(f"   [{check.status}] {check.name}: {check.message}")
        if result.status == "FAIL":
            code = max(code, 1)
    return code


def main() -> None:
    parser = argparse.ArgumentParser(prog="controlplane")
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("eval", help="run a golden suite against one runtime/model")
    ev.add_argument("--runtime", choices=["ollama", "mlx"], required=True)
    ev.add_argument("--model", required=True)
    ev.add_argument("--suite", choices=[*SUITES, "all"], default="all")
    ev.add_argument("--split", choices=["validation", "test"], default="validation")
    ev.add_argument("--limit", type=int, default=None)
    ev.add_argument("--max-tokens", type=int, default=1024)
    ev.add_argument("--think", choices=["default", "on", "off"], default="default")
    ev.add_argument("--guard", choices=["off", "on"], default="off")
    ev.add_argument(
        "--confirm-final",
        action="store_true",
        help="required for --split test: acknowledges the configuration is frozen",
    )
    ev.add_argument(
        "--allow-rerun",
        action="store_true",
        help="allow a second test-split run of the same configuration (breaks the one-shot rule)",
    )
    ev.add_argument("--base-url", default=None)
    ev.add_argument("--out", type=Path, default=Path("runs"))
    gate = sub.add_parser(
        "gate", help="compare run reports with committed baselines (exit 1 on FAIL)"
    )
    gate.add_argument("reports", nargs="+", type=Path, help="run directories or report.json files")
    gate.add_argument("--baselines", type=Path, default=Path("baselines"))
    gate.add_argument("--tolerance", type=int, default=2, help="allowed pass-count drop in cases")
    base = sub.add_parser("baseline-save", help="copy run reports into the baselines directory")
    base.add_argument("reports", nargs="+", type=Path)
    base.add_argument("--baselines", type=Path, default=Path("baselines"))
    dash = sub.add_parser("dashboard", help="build the single-page HTML dashboard from runs/")
    dash.add_argument("--runs", type=Path, default=Path("runs"))
    dash.add_argument("--out", type=Path, default=Path("docs/dashboard.html"))
    args = parser.parse_args()

    if args.command == "gate":
        raise SystemExit(run_gate(args.reports, args.baselines, args.tolerance))
    if args.command == "baseline-save":
        for path in map(_report_path, args.reports):
            args.baselines.mkdir(parents=True, exist_ok=True)
            target = args.baselines / f"{baseline_key(load_report(path)['meta'])}.json"
            shutil.copy(path, target)
            print(f"saved {target}")
        return
    if args.command == "dashboard":
        print(build_dashboard(args.runs, args.out))
        return

    if args.split == "test" and not args.confirm_final:
        raise SystemExit(
            "test split is one-shot and final: pass --confirm-final once the "
            "configuration is frozen"
        )

    client = build_client(args.runtime, args.base_url)
    names = list(SUITES) if args.suite == "all" else [args.suite]
    for name in names:
        cases = load_cases(SUITES[name], split=args.split)
        if args.limit:
            cases = cases[: args.limit]
        think = {"default": None, "on": True, "off": False}[args.think]
        if args.split == "test" and not args.allow_rerun:
            prior = test_run_exists(
                args.out, args.runtime, args.model, name, think, args.guard == "on", args.max_tokens
            )
            if prior is not None:
                raise SystemExit(
                    f"{name}: this configuration already has a test-split run "
                    f"({prior.name}); the test split is one-shot (--allow-rerun to override)"
                )
        run_dir = run_eval(
            client,
            args.model,
            cases,
            name,
            args.split,
            args.out,
            args.max_tokens,
            think,
            guard=args.guard == "on",
        )
        print(f"{name}: {run_dir}")
        print((run_dir / "report.md").read_text())


if __name__ == "__main__":
    main()
