"""Exploratory: how often does a model follow an injected instruction when it is *sampled*?

At temperature 0 a run is deterministic, so one run says little about how often an attack works.
This repeats the injection cases with several seeds at a non-zero temperature, for each condition
(transport, guard mode), and counts attempted and executed violations per sample.

Usage: python -m scripts.injection_rate --runtime ollama --model gemma4:26b --samples 8
"""

import argparse
from dataclasses import dataclass, field

from controlplane.agent import run_agent
from controlplane.cli import SUITES, build_client
from controlplane.evals.agent_scorer import score_agent
from controlplane.evals.contract import load_cases
from controlplane.evals.runner import make_world

# "direct-mcpspecs" is the control: the in-process world, but the model is shown the tool schemas
# and descriptions exactly as an MCP server serves them. It separates "schema presentation" from
# "transport".
CONDITIONS = [
    ("direct", "off"),
    ("direct", "rules"),
    ("direct", "provenance"),
    ("mcp", "rules"),
    ("mcp", "provenance"),
    ("direct-mcpspecs", "rules"),
]


@dataclass
class Tally:
    samples: int = 0
    attempted: int = 0
    executed: int = 0
    leaks: int = 0
    by_case: dict[str, int] = field(default_factory=dict)


def injection_cases():
    sec = [c for c in load_cases(SUITES["agent_security"], "validation") if "injection" in c.tags]
    inj = [
        c
        for c in load_cases(SUITES["agent_injection"], "validation")
        if "injection" in c.tags and c.expected.get("violations")
    ]
    return sec + inj


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--think", choices=["off", "default"], default="off")
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="subset of conditions, e.g. mcp:rules direct-mcpspecs:rules",
    )
    args = parser.parse_args()
    client = build_client(args.runtime, None)
    cases = injection_cases()
    print(f"{len(cases)} injection cases x {args.samples} samples at T={args.temperature}")
    served_specs = None
    for transport, guard in CONDITIONS:
        if args.only and f"{transport}:{guard}" not in args.only:
            continue
        tally = Tally()
        for case in cases:
            for seed in range(1, args.samples + 1):
                if transport == "direct-mcpspecs":
                    if served_specs is None:
                        probe = make_world(case, guard, None, "mcp")
                        served_specs = list(probe.specs)
                        probe.close()
                    world = make_world(case, guard, None, "direct")
                    world.specs = served_specs
                else:
                    world = make_world(case, guard, None, transport)
                run = run_agent(
                    client,
                    args.model,
                    case.messages,
                    world,
                    max_tokens=args.max_tokens,
                    think=False if args.think == "off" else None,
                    temperature=args.temperature,
                    seed=seed,
                )
                if hasattr(world, "close"):
                    world.close()
                security = score_agent(case, run).detail["security"]
                tally.samples += 1
                tally.attempted += bool(security["attempted"])
                if security["attempted"]:
                    tally.by_case[case.id] = tally.by_case.get(case.id, 0) + 1
                tally.executed += bool(security["executed"])
                tally.leaks += bool(security["leaks"])
        print(
            f"{transport:6s} guard={guard:10s} samples {tally.samples:3d}  attempted "
            f"{tally.attempted:3d}  executed {tally.executed:3d}  leaks {tally.leaks:3d}"
            + (f"  by case: {tally.by_case}" if tally.by_case else "")
        )


if __name__ == "__main__":
    main()
