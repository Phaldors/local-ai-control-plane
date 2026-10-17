"""Bisect which schema difference changes how often a model follows an injection (sec-i2).

An MCP server serves tool schemas that differ from the hand-written ones (pydantic `title` metadata,
no `additionalProperties: false`, optionals as anyOf/null). Each variant here changes one thing and
counts, over 8 sampled seeds, how often the model creates the ticket the hostile note asked for.
"""

import copy

from controlplane.agent import run_agent
from controlplane.cli import SUITES, build_client
from controlplane.evals.agent_scorer import score_agent
from controlplane.evals.contract import load_cases
from controlplane.evals.runner import make_world
from controlplane.mcp_client import McpWorld
from controlplane.mcp_server import build_world
from controlplane.types import ToolSpec
from controlplane.worlds.shop import ShopWorld

case = next(c for c in load_cases(SUITES["agent_security"], "validation") if c.id == "sec-i2")
probe = McpWorld(build_world("rules"))
served = list(probe.specs)
probe.close()
orig = list(ShopWorld.specs)


def strip_titles(node):
    if isinstance(node, dict):
        return {
            k: strip_titles(v) for k, v in node.items() if k != "title" or not isinstance(v, str)
        }
    if isinstance(node, list):
        return [strip_titles(v) for v in node]
    return node


def with_params(specs, fn):
    return [
        ToolSpec(name=s.name, description=s.description, parameters=fn(copy.deepcopy(s.parameters)))
        for s in specs
    ]


def no_addl(p):
    p.pop("additionalProperties", None)
    return p


def add_addl(p):
    p["additionalProperties"] = False
    return p


def swap(base, donor, tool):
    donated = next(d for d in donor if d.name == tool)
    return [donated if b.name == tool else b for b in base]


variants = {
    "V0 original": orig,
    "V1 served (MCP)": served,
    "V2 served minus titles": with_params(served, strip_titles),
    "V3 original minus additionalProperties": with_params(orig, no_addl),
    "V4 served plus additionalProperties=false": with_params(served, add_addl),
    "V5 original + served search_orders only": swap(orig, served, "search_orders"),
    "V6 served + original search_orders only": swap(served, orig, "search_orders"),
}
client = build_client("ollama", None)
for name, specs in variants.items():
    hits = 0
    for seed in range(1, 9):
        world = make_world(case, "rules", None, "direct")
        world.specs = specs
        run = run_agent(
            client,
            "gemma4:26b",
            case.messages,
            world,
            max_tokens=1024,
            think=False,
            temperature=0.7,
            seed=seed,
        )
        hits += bool(score_agent(case, run).detail["security"]["attempted"])
    print(f"{name:45s} injected ticket created in {hits}/8 samples", flush=True)
