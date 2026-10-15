"""Apply the leak detector to existing runs (traces.jsonl + report.json) and print the rate per run.

Only runs whose configuration requested thinking off are considered.
"""

import json
from pathlib import Path

from controlplane.reasoning import looks_like_leaked_reasoning


def main(runs_dir: Path = Path("runs")) -> None:
    rows = []
    for run in sorted(runs_dir.iterdir()):
        report, traces = run / "report.json", run / "traces.jsonl"
        if not (report.exists() and traces.exists()):
            continue
        meta = json.loads(report.read_text())["meta"]
        if meta.get("think") is not False:
            continue
        calls = [json.loads(line) for line in traces.read_text().splitlines() if line.strip()]
        calls = [c for c in calls if c.get("status") == "ok"]
        leaked = sum(looks_like_leaked_reasoning(c.get("output") or "") for c in calls)
        rows.append(
            (meta["runtime"], meta["model"].split("/")[-1], meta["suite"], len(calls), leaked)
        )
    by_config: dict[tuple[str, str], list[int]] = {}
    for runtime, model, _suite, n, leaked in rows:
        agg = by_config.setdefault((runtime, model), [0, 0])
        agg[0] += n
        agg[1] += leaked
    for (runtime, model), (n, leaked) in sorted(by_config.items()):
        print(
            f"{runtime:7s} {model:22s} think-off calls {n:5d}  leaked {leaked:5d}  "
            f"rate {leaked / n:6.1%}"
        )


if __name__ == "__main__":
    main()
