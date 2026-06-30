"""Inspect T4 results — per-scenario breakdown + failure-mode classification.

Usage:
    python scripts/analyze_t4.py [--results data/results/t4-prod-n100.json]
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="data/results/t4-prod-n100.json")
    ap.add_argument("--show-failures", type=int, default=4,
                    help="how many sample failure cases to print per category")
    args = ap.parse_args()

    d = json.loads(Path(args.results).read_text())
    rows = d["rows"]

    # Summary table
    print("=" * 70)
    print(f"{'system':<18} {'pd_recall':>12} {'agg_recall':>12} {'n_scored':>10}")
    print("-" * 70)
    for s, m in d["summary"].items():
        print(f"{s:<18} {m['per_detail_recall']:>12.3f} "
              f"{m['aggregate_recall']:>12.3f} {m['n_scored']:>10}")

    # Per-scenario breakdown (only meaningful for non-zero systems)
    for sys_name in d["summary"]:
        if d["summary"][sys_name]["per_detail_recall"] == 0.0:
            continue
        sys_rows = [r for r in rows if r["system"] == sys_name and not r.get("error")]
        by_scenario = {}
        for r in sys_rows:
            by_scenario.setdefault(r.get("scenario", "?"), []).append(r)
        print(f"\n=== {sys_name} — per-scenario breakdown ===")
        for sc, rs in sorted(by_scenario.items()):
            pd = sum(r["per_detail"]["recall"] for r in rs) / len(rs)
            ag = sum(r["aggregate"]["recall"] for r in rs) / len(rs)
            print(f"  {sc:14} n={len(rs):3}  per_detail={pd:.3f}  aggregate={ag:.3f}")

    # Failure mode classification (per-detail probes only — per-probe data)
    for sys_name in d["summary"]:
        if d["summary"][sys_name]["per_detail_recall"] in (0.0, 1.0):
            continue  # nothing or everything missed — boring
        sys_rows = [r for r in rows if r["system"] == sys_name and not r.get("error")]
        unknown = []
        wrong_value = []
        for r in sys_rows:
            for p in r["per_detail"]["per_probe"]:
                if p["hit"]:
                    continue
                if "unknown" in p["answer"].lower():
                    unknown.append((r["case_id"], p["key"], p["expected"], p["answer"]))
                else:
                    wrong_value.append((r["case_id"], p["key"], p["expected"], p["answer"]))
        total = len(unknown) + len(wrong_value)
        if total == 0:
            continue
        print(f"\n=== {sys_name} — per-detail failure modes (n={total}) ===")
        print(f"  'unknown' (memory had no value to give):  "
              f"{len(unknown):>4} ({len(unknown)*100/total:.1f}%)")
        print(f"  wrong value (hallucinated from pool):     "
              f"{len(wrong_value):>4} ({len(wrong_value)*100/total:.1f}%)")

        if args.show_failures > 0:
            print(f"\n  Sample 'unknown' misses:")
            for cid, k, exp, ans in unknown[:args.show_failures]:
                print(f"    {cid} [{k}]: expected '{exp}', got: {ans[:60]!r}")
            print(f"\n  Sample 'wrong value' misses:")
            for cid, k, exp, ans in wrong_value[:args.show_failures]:
                print(f"    {cid} [{k}]: expected '{exp}', got: {ans[:60]!r}")


if __name__ == "__main__":
    main()
