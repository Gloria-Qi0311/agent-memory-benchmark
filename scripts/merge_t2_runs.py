"""Merge two T2 experiment result files into a combined view.

Same shape as scripts/merge_t4_runs.py but for T2's schema. Case IDs
across the two runs must be disjoint (guaranteed by non-overlapping
seed ranges when generating cases).

Systems that appear in one input but not the other are kept as-is
(useful when e.g. pure_vector was run at n=100 but skipped at n=200).

Usage:
    python scripts/merge_t2_runs.py \
        --inputs data/results/t2-prod-n100-5sys.json \
                 data/results/t2-prod-n200-s200-4sys.json \
        --out data/results/t2-prod-n300-merged.json
"""
import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def merge(inputs: list[Path]) -> dict:
    # Latest input for a given (system, case_id) wins.
    seen: dict[tuple[str, str], dict] = {}
    for path in inputs:
        data = load(path)
        for row in data["rows"]:
            key = (row["system"], row["case_id"])
            seen[key] = row
    rows = list(seen.values())

    per_system: dict[str, dict] = {}
    for r in rows:
        s = r["system"]
        per_system.setdefault(s, {"upd": [], "conf": [], "coll": [],
                                    "errors": 0, "n_total": 0})
        per_system[s]["n_total"] += 1
        if r.get("error"):
            per_system[s]["errors"] += 1
            continue
        per_system[s]["upd"].append(r["score"]["update_recall"])
        per_system[s]["conf"].append(r["score"]["no_confusion"])
        per_system[s]["coll"].append(r["score"]["no_collateral"])

    summary = {}
    for s, acc in per_system.items():
        def _mean(xs): return sum(xs) / len(xs) if xs else 0.0
        summary[s] = {
            "n_total": acc["n_total"],
            "n_scored": len(acc["upd"]),
            "n_errors": acc["errors"],
            "update_recall": _mean(acc["upd"]),
            "no_confusion": _mean(acc["conf"]),
            "no_collateral": _mean(acc["coll"]),
        }
    source_metadata = [load(path).get("metadata", {}) for path in inputs]
    return {
        "metadata": {
            "merged_from": [str(path) for path in inputs],
            "judge": "t2-exact-v3-token-boundary-plus-authored-aliases",
            "llm_calls_for_rescore": 0,
            "excluded_case_ids": sorted({
                case_id
                for metadata in source_metadata
                for case_id in metadata.get("excluded_case_ids", [])
            }),
            "changed_probe_judgments": sum(
                metadata.get("changed_probe_judgments", 0)
                for metadata in source_metadata
            ),
            "known_invalid_systems": sorted({
                system
                for metadata in source_metadata
                for system in metadata.get("known_invalid_systems", [])
            }),
            "invalid_system_reason": next(
                (metadata.get("invalid_system_reason") for metadata in source_metadata
                 if metadata.get("invalid_system_reason")),
                None,
            ),
        },
        "summary": summary,
        "rows": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
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

    print(f"Merged {len(inputs)} files -> {out}")
    print(f"{'system':<18} {'upd_recall':>12} {'no_confusion':>14} "
          f"{'no_collateral':>14} {'n_scored':>10}")
    print("-" * 78)
    for s, m in merged["summary"].items():
        print(f"{s:<18} {m['update_recall']:>12.3f} "
              f"{m['no_confusion']:>14.3f} {m['no_collateral']:>14.3f} "
              f"{m['n_scored']:>10}")


if __name__ == "__main__":
    main()
