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
import random


def bootstrap_ci(values: list[float], repeats: int = 10_000) -> tuple[float, float]:
    """Deterministic case-level percentile bootstrap CI for a mean."""
    if not values:
        return 0.0, 0.0
    rng = random.Random(20260821)
    n = len(values)
    means = sorted(
        sum(rng.choice(values) for _ in range(n)) / n
        for _ in range(repeats)
    )
    return means[int(0.025 * repeats)], means[int(0.975 * repeats) - 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="data/results/t2-prod-n300-merged.json")
    ap.add_argument("--show-failures", type=int, default=4,
                    help="how many sample collateral-damage cases to print per system")
    args = ap.parse_args()

    d = json.loads(Path(args.results).read_text())
    rows = d["rows"]
    invalid_systems = set(d.get("metadata", {}).get("known_invalid_systems", []))

    if invalid_systems:
        print("WARNING: scores marked * are retained historical diagnostics, not publishable results.")
        print(d["metadata"].get("invalid_system_reason", "Known-invalid system run."))
        print()

    # Summary
    print("=" * 78)
    print(f"{'system':<18} {'upd_recall [95% CI]':>25} "
          f"{'no_conf [95% CI]':>23} {'no_coll [95% CI]':>23} {'n':>5}")
    print("-" * 78)
    for s, m in d["summary"].items():
        if s in invalid_systems:
            print(f"{s + '*':<18} {'INVALID — rerun required':>25} "
                  f"{'INVALID':>23} {'INVALID':>23} {m['n_scored']:>5}")
            continue
        system_rows = [r for r in rows if r["system"] == s and not r.get("error")]
        cells = []
        for metric in ("update_recall", "no_confusion", "no_collateral"):
            values = [r["score"][metric] for r in system_rows]
            lo, hi = bootstrap_ci(values)
            cells.append(f"{m[metric]:.3f} [{lo:.3f}, {hi:.3f}]")
        print(f"{s:<18} {cells[0]:>25} {cells[1]:>23} {cells[2]:>23} "
              f"{m['n_scored']:>5}")

    # Per-scenario
    for sys_name in d["summary"]:
        if sys_name in invalid_systems:
            continue
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

    # Collateral failure classification. This runs only after the current
    # judge has established a real miss; punctuation/product-name matches are
    # therefore no longer mislabeled as concrete wrong answers.
    print()
    for sys_name in d["summary"]:
        if sys_name in invalid_systems:
            continue
        if d["summary"][sys_name]["no_collateral"] >= 1.0:
            continue
        sys_rows = [r for r in rows if r["system"] == sys_name and not r.get("error")]
        unknown_misses = []
        concrete_misses = []
        for r in sys_rows:
            for p in r["score"]["per_probe"]:
                if p["kind"] != "preserved" or p["hit"]:
                    continue
                if "unknown" in p["answer"].lower():
                    unknown_misses.append((r["case_id"], p["key"], p["expected"], p["answer"]))
                else:
                    concrete_misses.append((r["case_id"], p["key"], p["expected"], p["answer"]))
        total = len(unknown_misses) + len(concrete_misses)
        if total == 0:
            continue
        print(f"=== {sys_name} — preserved-probe misses breakdown (n={total}) ===")
        print(f"  'unknown' (memory dropped it):           "
              f"{len(unknown_misses):>4} ({len(unknown_misses)*100/total:.1f}%)")
        print(f"  other concrete answer:                  "
              f"{len(concrete_misses):>4} ({len(concrete_misses)*100/total:.1f}%)")
        if args.show_failures > 0 and concrete_misses:
            print(f"\n  Sample concrete-answer misses:")
            for cid, k, exp, ans in concrete_misses[:args.show_failures]:
                print(f"    {cid} [{k}]: expected '{exp}', got: {ans[:70]!r}")
        print()


if __name__ == "__main__":
    main()
