"""Merge two T4 experiment result files into a single combined summary.

Used to combine an initial n=N1 run with an extension n=N2 run into a
unified n=(N1+N2) view without re-running any cases. Case IDs across the
two runs must be disjoint (guaranteed by using non-overlapping seed
ranges when generating cases).

Usage:
    python scripts/merge_t4_runs.py \
        --inputs data/results/t4-repro-n100-5sys.json \
                 data/results/t4-repro-n200-s200-5sys.json \
        --out /tmp/t4-repro-n300-merged.json
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_result(path: Path) -> dict:
    return json.loads(path.read_text())


def merge(inputs: list[Path]) -> dict:
    # Collect all rows, deduping by (system, case_id) so re-runs of same
    # case don't double-count (latest input wins).
    seen: dict[tuple[str, str], dict] = {}
    for path in inputs:
        data = load_result(path)
        for row in data["rows"]:
            key = (row["system"], row["case_id"])
            seen[key] = row
    rows = list(seen.values())

    # Recompute summary from merged rows
    per_system: dict[str, dict] = {}
    for r in rows:
        s = r["system"]
        per_system.setdefault(s, {"pd": [], "agg": [], "errors": 0, "n_total": 0})
        per_system[s]["n_total"] += 1
        if r.get("error"):
            per_system[s]["errors"] += 1
            continue
        per_system[s]["pd"].append(r["per_detail"]["recall"])
        per_system[s]["agg"].append(r["aggregate"]["recall"])

    summary = {}
    for s, acc in per_system.items():
        def _mean(xs): return sum(xs) / len(xs) if xs else 0.0
        summary[s] = {
            "n_total": acc["n_total"],
            "n_scored": len(acc["pd"]),
            "n_errors": acc["errors"],
            "per_detail_recall": _mean(acc["pd"]),
            "aggregate_recall": _mean(acc["agg"]),
        }
    return {"summary": summary, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="two or more T4 result JSON files")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inputs = [Path(p) for p in args.inputs]
    for p in inputs:
        if not p.exists():
            raise SystemExit(f"input not found: {p}")

    merged = merge(inputs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=2))

    # Print quick summary
    print(f"Merged {len(inputs)} files -> {out}")
    print(f"{'system':<18} {'pd_recall':>12} {'agg_recall':>12} {'n_scored':>10}")
    print("-" * 60)
    for s, m in merged["summary"].items():
        print(f"{s:<18} {m['per_detail_recall']:>12.3f} "
              f"{m['aggregate_recall']:>12.3f} {m['n_scored']:>10}")


if __name__ == "__main__":
    main()
