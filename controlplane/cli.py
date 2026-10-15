import argparse
from pathlib import Path

from controlplane.client import LLMClient
from controlplane.evals.contract import load_cases
from controlplane.evals.runner import run_eval
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
    ev.add_argument("--base-url", default=None)
    ev.add_argument("--out", type=Path, default=Path("runs"))
    args = parser.parse_args()

    if args.split == "test":
        print("WARNING: test split is for the final frozen report only.")

    client = build_client(args.runtime, args.base_url)
    names = list(SUITES) if args.suite == "all" else [args.suite]
    for name in names:
        cases = load_cases(SUITES[name], split=args.split)
        if args.limit:
            cases = cases[: args.limit]
        think = {"default": None, "on": True, "off": False}[args.think]
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
