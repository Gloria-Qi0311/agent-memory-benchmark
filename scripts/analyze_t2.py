"""Inspect T2 (compound update) results.

Prints:
  - summary table (system x update_recall x no_confusion x no_collateral)
  - per-scenario breakdown
  - collateral-damage failure detail: for each system, how often did a
    preserved fact get answered with a plausible-but-wrong value vs
    'unknown'

Usage:
    python scripts/analyze_t2.py [--results data/results/t2-prod-n300-merged.json]
"""
import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="data/results/t2-prod-n300-merged.json")
    ap.add_argument("--show-failures", type=int, default=4,
                    help="how many sample collateral-damage cases to print per system")
    args = ap.parse_args()

    d = json.loads(Path(args.results).read_text())
    rows = d["rows"]

    # Summary
    print("=" * 78)
    print(f"{'system':<18} {'upd_recall':>12} {'no_conf':>10} "
          f"{'no_coll':>10} {'n_scored':>10}")
    print("-" * 78)
    for s, m in d["summary"].items():
        print(f"{s:<18} {m['update_recall']:>12.3f} "
              f"{m['no_confusion']:>10.3f} {m['no_collateral']:>10.3f} "
              f"{m['n_scored']:>10}")

    # Per-scenario
    for sys_name in d["summary"]:
        if d["summary"][sys_name]["update_recall"] == 0.0:
            continue
        sys_rows = [r for r in rows if r["system"] == sys_name and not r.get("error")]
        by_scenario = {}
        for r in sys_rows:
            by_scenario.setdefault(r.get("scenario", "?"), []).append(r)
        print(f"\n=== {sys_name} — per-scenario ===")
        for sc, rs in sorted(by_scenario.items()):
            def _m(k): return sum(r["score"][k] for r in rs) / len(rs)
            print(f"  {sc:14} n={len(rs):3}  "
                  f"upd={_m('update_recall'):.3f}  "
                  f"no_conf={_m('no_confusion'):.3f}  "
                  f"no_coll={_m('no_collateral'):.3f}")

    # Collateral damage failure classification: for each system, break
    # down preserved-probe misses by "unknown" vs "wrong-value hallucination"
    print()
    for sys_name in d["summary"]:
        if d["summary"][sys_name]["no_collateral"] >= 1.0:
            continue
        sys_rows = [r for r in rows if r["system"] == sys_name and not r.get("error")]
        unknown_misses = []
        wrong_value_misses = []
        for r in sys_rows:
            for p in r["score"]["per_probe"]:
                if p["kind"] != "preserved" or p["hit"]:
                    continue
                if "unknown" in p["answer"].lower():
                    unknown_misses.append((r["case_id"], p["key"], p["expected"], p["answer"]))
                else:
                    wrong_value_misses.append((r["case_id"], p["key"], p["expected"], p["answer"]))
        total = len(unknown_misses) + len(wrong_value_misses)
        if total == 0:
            continue
        print(f"=== {sys_name} — preserved-probe misses breakdown (n={total}) ===")
        print(f"  'unknown' (memory dropped it):           "
              f"{len(unknown_misses):>4} ({len(unknown_misses)*100/total:.1f}%)")
        print(f"  wrong value (silent collateral damage):  "
              f"{len(wrong_value_misses):>4} ({len(wrong_value_misses)*100/total:.1f}%)")
        if args.show_failures > 0 and wrong_value_misses:
            print(f"\n  Sample wrong-value collateral damages:")
            for cid, k, exp, ans in wrong_value_misses[:args.show_failures]:
                print(f"    {cid} [{k}]: expected '{exp}', got: {ans[:70]!r}")
        print()


if __name__ == "__main__":
    main()
