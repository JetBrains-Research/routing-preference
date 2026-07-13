"""Estimate a standardized completion time for every generated solution.

Wall-clock durations depend on provider routing, machine load, and incident
noise, so the displayed completion time is modeled from run quantities under
the model's nominal serving conditions instead:

    time = calls x ttft_p50_seconds          (per-call overhead)
         + completion_tokens / speed_tps     (generation)
         + steps x COMMAND_SECONDS           (command execution)

ttft_p50_seconds and best_openrouter_speed_tps come from configs/models.yaml
(per model, externally sourced). COMMAND_SECONDS is measured from the trajectories
themselves; --sensitivity reports how little the ordering depends on it.

Usage:
    python scripts/estimate_completion_times.py [--sensitivity]

Writes data/exports/estimated_completion_times.json.
"""

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
SOLUTIONS_DIR = ROOT / "data" / "solutions"
MODELS_CONFIG = ROOT / "configs" / "models.yaml"
OUTPUT = ROOT / "data" / "exports" / "estimated_completion_times.json"

# Timeout-trimmed mean of 3,974 command durations measured directly from the
# generation trajectories (commands hitting the 120s/600s timeout excluded).
COMMAND_SECONDS = 0.56


def model_constants() -> dict[str, dict]:
    config = yaml.safe_load(MODELS_CONFIG.read_text(encoding="utf-8"))
    constants = {}
    for entry in config["models"].values():
        openrouter = entry["providers"]["openrouter"]
        slug = "openrouter_" + openrouter["openrouter_id"].replace("/", "_")
        constants[slug] = {
            "tps": float(entry["best_openrouter_speed_tps"]),
            "ttft": float(openrouter["ttft_p50_seconds"]),
        }
    return constants


def run_quantities(run_dir: Path) -> dict:
    solution = json.loads((run_dir / "solution.json").read_text(encoding="utf-8"))
    info = json.loads((run_dir / "info.json").read_text(encoding="utf-8"))
    calls = completion_tokens = 0
    for message in solution["trajectory"]["messages"]:
        if message.get("role") != "assistant":
            continue
        calls += 1
        usage = (message.get("extra", {}).get("response") or {}).get("usage") or {}
        completion_tokens += usage.get("completion_tokens", 0) or 0
    return {
        "calls": calls,
        "completion_tokens": completion_tokens,
        "steps": info["objective_metrics"]["step_count"],
        "measured_seconds": solution["duration_ms"] / 1000,
    }


def estimate(q: dict, c: dict, command_seconds: float = COMMAND_SECONDS) -> float:
    return (
        q["calls"] * c["ttft"]
        + q["completion_tokens"] / c["tps"]
        + q["steps"] * command_seconds
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensitivity", action="store_true")
    args = parser.parse_args()

    constants = model_constants()
    entries = []
    for run_dir in sorted(SOLUTIONS_DIR.glob("0*/openrouter_*/2*")):
        slug = run_dir.parent.name
        q = run_quantities(run_dir)
        entries.append(
            {
                "task_id": run_dir.parts[-3],
                "model_slug": slug,
                "run_id": run_dir.name,
                "solution_id": f"{slug}__{run_dir.name}",
                **q,
                "estimated_seconds": round(estimate(q, constants[slug])),
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "method": (
                    "calls*ttft_p50 + completion_tokens/speed_tps + "
                    f"steps*{COMMAND_SECONDS}s; per-model constants from "
                    "configs/models.yaml"
                ),
                "solutions": entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT} ({len(entries)} solutions)")

    if args.sensitivity:
        _sensitivity(entries, constants)


def _spearman(xs: list[float], ys: list[float]) -> float:
    def ranks(vals):
        order = sorted(range(len(vals)), key=vals.__getitem__)
        r = [0.0] * len(vals)
        for rank, idx in enumerate(order):
            r[idx] = rank
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx = my = (n - 1) / 2
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    return cov / (vx * vy) ** 0.5


def _sensitivity(entries: list[dict], constants: dict) -> None:
    base = [e["estimated_seconds"] for e in entries]
    measured = [e["measured_seconds"] for e in entries]
    print(f"validation: Spearman(estimated, measured) = "
          f"{_spearman(base, measured):.3f} over {len(entries)} solutions")
    for label, ttft_scale, cmd in (
        ("2x ttft, 3s/command", 2.0, 3.0),
        ("0.5x ttft, 0.5s/command", 0.5, 0.5),
    ):
        alt = []
        for e in entries:
            c = constants[e["model_slug"]]
            scaled = {"tps": c["tps"], "ttft": c["ttft"] * ttft_scale}
            alt.append(estimate(e, scaled, cmd))
        print(f"sensitivity ({label}): Spearman vs base = "
              f"{_spearman(base, alt):.3f}")


if __name__ == "__main__":
    main()
