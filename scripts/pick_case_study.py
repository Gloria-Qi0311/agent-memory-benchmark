"""Pick T4 cases that best illustrate the finding for a writeup.

A "good case study" is one where the qualitative story is clearest:
  - naive_markdown / pure_vector / amh all scored high (≥ 0.85)
  - mem0 scored significantly lower (≤ 0.60)
  - preferably in a scenario that hasn't already been used

Prints the case ID, the user statement, and mem0's per-detail
answers side-by-side with the ground truth for the sharpest failures.

Usage:
    python scripts/pick_case_study.py \
        --results data/results/t4-prod-n300-merged.json \
        --cases data/cases/split_intake_n100_s100.json data/cases/split_intake_n200_s200.json
"""
import argparse
import json
from pathlib import Path


def load_cases(paths: list[Path]) -> dict[str, dict]:
    out = {}
    for p in paths:
        for case in json.loads(p.read_text()):
            out[case["case_id"]] = case
    return out


def pick_candidates(rows: list[dict], top_n: int = 5) -> list[str]:
    """Rank cases by |mem0 recall - min(other systems' recalls)|.
    We want cases where mem0 tanks but the extraction-free trio all did well."""
    by_case: dict[str, dict[str, float]] = {}
    for r in rows:
        if r.get("error"):
            continue
        cid = r["case_id"]
        by_case.setdefault(cid, {})
        by_case[cid][r["system"]] = r["per_detail"]["recall"]

    scored = []
    for cid, sysmap in by_case.items():
        extraction_free = [
            sysmap.get("naive_markdown", 0),
            sysmap.get("pure_vector", 0),
            sysmap.get("amh", 0),
        ]
        mem0 = sysmap.get("mem0", 1.0)
        # only consider cases where all extraction-free are ≥ 0.85
        if min(extraction_free) < 0.85:
            continue
        # only cases where mem0 is ≤ 0.60
        if mem0 > 0.60:
            continue
        # gap = min extraction-free minus mem0
        gap = min(extraction_free) - mem0
        scored.append((gap, cid))
    scored.sort(reverse=True)
    return [cid for _, cid in scored[:top_n]]


def print_case_study(cid: str, case: dict, mem0_row: dict) -> None:
    print("=" * 72)
    print(f"Case: {cid} | scenario: {case['scenario']} | persona: {case['persona']}")
    print("=" * 72)
    print("\nUser statement:")
    print(f"  {case['user_statement']}\n")
    print(f"mem0 per_detail recall: {mem0_row['per_detail']['recall']:.2f}\n")
    print("Probe-by-probe (per_detail mode):")
    print(f"  {'key':<18} {'ground truth':<28} {'mem0 answered':<40} {'hit'}")
    print(f"  {'-'*18} {'-'*28} {'-'*40} {'---'}")
    for p in mem0_row["per_detail"]["per_probe"]:
        ans = p["answer"].replace("\n", " ")[:38]
        flag = "✓" if p["hit"] else "✗"
        print(f"  {p['key']:<18} {p['expected']:<28} {ans:<40} {flag}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--cases", nargs="+", required=True)
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()

    data = json.loads(Path(args.results).read_text())
    cases = load_cases([Path(p) for p in args.cases])

    top_cids = pick_candidates(data["rows"], top_n=args.top)
    print(f"Selected top {len(top_cids)} case studies:\n")
    for cid in top_cids:
        mem0_row = next(
            r for r in data["rows"]
            if r["case_id"] == cid and r["system"] == "mem0"
        )
        print_case_study(cid, cases[cid], mem0_row)


if __name__ == "__main__":
    main()
