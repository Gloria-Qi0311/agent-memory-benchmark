"""Inspect a rewrite-experiment result file.

Usage:
    python scripts/analyze_rewrite.py data/results/rewrite-n200.json

Prints:
  - summary table (system x metric)
  - per-system failure breakdown (kind of miss, sample cases)
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_file")
    ap.add_argument("--show-failures", type=int, default=5,
                    help="how many failure cases to print per system")
    args = ap.parse_args()

    d = json.loads(Path(args.results_file).read_text())
    print(f"Loaded: {args.results_file}\n")

    # Summary table
    print("=" * 80)
    print(f"{'system':<18} {'n_scored':>10} {'pf_upd':>8} {'pf_pres':>8} {'ag_upd':>8} {'ag_pres':>8}")
    print("-" * 80)
    for sys_name, s in d["summary"].items():
        print(
            f"{sys_name:<18} {s['n_scored']:>10} "
            f"{s['per_fact']['update_correct_rate']:>8.2%} "
            f"{s['per_fact']['preservation_rate']:>8.2%} "
            f"{s['aggregate']['update_correct_rate']:>8.2%} "
            f"{s['aggregate']['preservation_rate']:>8.2%}"
        )

    # Per-system failure analysis
    print("\n" + "=" * 80)
    print("Failure analysis")
    print("=" * 80)
    for sys_name in d["summary"]:
        rows = [r for r in d["rows"] if r["system"] == sys_name and not r.get("error")]
        # Group failures by kind
        per_fact_update_misses = []
        per_fact_pres_misses = []  # cases where any preserved fact got mangled
        for r in rows:
            pf = r.get("per_fact", {})
            if pf.get("update_correct") == 0:
                per_fact_update_misses.append(r)
            if pf.get("preservation_rate", 1.0) < 1.0:
                per_fact_pres_misses.append(r)

        print(f"\n--- {sys_name} ---")
        print(f"  per_fact update misses:       {len(per_fact_update_misses)} / {len(rows)}")
        print(f"  per_fact preservation misses: {len(per_fact_pres_misses)} / {len(rows)}")

        # Show sample failures with the exact wrong answer
        if per_fact_update_misses and args.show_failures:
            print(f"\n  Sample update misses (system returned wrong value for the updated fact):")
            for r in per_fact_update_misses[:args.show_failures]:
                for p in r["per_fact"]["per_probe"]:
                    if p["kind"] == "updated" and not p["hit"]:
                        print(f"    {r['case_id']}: expected '{p['expected']}', got: {p['answer'][:80]!r}")

        if per_fact_pres_misses and args.show_failures:
            print(f"\n  Sample preservation misses (system damaged an unrelated fact):")
            for r in per_fact_pres_misses[:args.show_failures]:
                for p in r["per_fact"]["per_probe"]:
                    if p["kind"] == "preserved" and not p["hit"]:
                        print(f"    {r['case_id']} [{p['category']}]: expected '{p['expected']}', got: {p['answer'][:80]!r}")


if __name__ == "__main__":
    main()
