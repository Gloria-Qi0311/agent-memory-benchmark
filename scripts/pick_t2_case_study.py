"""Pick T2 cases that best illustrate collateral damage for a writeup.

Selection criteria: mem0 scores much lower on no_collateral than the
non-extraction systems (naive_markdown, amh, pure_vector) do on the
same case. This surfaces mem0's silent-damage failure mode most sharply.

Usage:
    python scripts/pick_t2_case_study.py \
        --results data/results/t2-prod-n300-merged.json \
        --cases data/cases/compound_update_n100_s100.json \
                data/cases/compound_update_n200_s200.json
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


def pick(rows: list[dict], top_n: int = 5) -> list[str]:
    """Rank by max(collateral among extraction-free) minus mem0 collateral.
    Larger diff = starker contrast."""
    by_case: dict[str, dict[str, float]] = {}
    for r in rows:
        if r.get("error"):
            continue
        by_case.setdefault(r["case_id"], {})
        by_case[r["case_id"]][r["system"]] = r["score"]["no_collateral"]

    scored = []
    for cid, sysmap in by_case.items():
        if "mem0" not in sysmap:
            continue
        mem0 = sysmap["mem0"]
        extraction_free = [
            sysmap.get(s, 0.0) for s in ("naive_markdown", "pure_vector", "amh")
            if s in sysmap
        ]
        if not extraction_free:
            continue
        # Require the extraction-free systems to have done well (avoid
        # cases where nobody preserves).
        if min(extraction_free) < 0.7:
            continue
        # Require mem0 to have failed
        if mem0 > 0.5:
            continue
        gap = min(extraction_free) - mem0
        scored.append((gap, cid))
    scored.sort(reverse=True)
    return [cid for _, cid in scored[:top_n]]


def print_case(cid: str, case: dict, mem0_row: dict) -> None:
    print("=" * 76)
    print(f"Case: {cid} | scenario: {case['scenario']} | persona: {case['persona']}")
    print("=" * 76)
    print("\nInitial facts (agent_a wrote these one-by-one, Phase 1):")
    for k, v in case["initial_facts"].items():
        marker = "★" if k in case["updated_facts"] else " "
        print(f"  {marker} {k:18} = {v}")
    print(f"\nUpdate utterance (agent_b said this, Phase 2):")
    print(f"  {case['update_utterance']}")
    print(f"\nmem0's answers to probes (Phase 3):")
    print(f"  {'key':<18} {'expected':<25} {'mem0 answered':<40} {'✓/✗'}")
    print(f"  {'-'*18} {'-'*25} {'-'*40} {'---'}")
    for p in mem0_row["score"]["per_probe"]:
        ans = p["answer"].replace("\n", " ")[:38]
        flag = "✓" if p["hit"] else "✗"
        kind_marker = "★ upd" if p["kind"] == "updated" else "  pres"
        print(f"  {p['key']:<18} {p['expected']:<25} {ans:<40} {flag} {kind_marker}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--cases", nargs="+", required=True)
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()

    data = json.loads(Path(args.results).read_text())
    cases = load_cases([Path(p) for p in args.cases])

    top_cids = pick(data["rows"], top_n=args.top)
    print(f"Selected top {len(top_cids)} case studies:\n")
    for cid in top_cids:
        try:
            mem0_row = next(
                r for r in data["rows"]
                if r["case_id"] == cid and r["system"] == "mem0"
            )
        except StopIteration:
            continue
        print_case(cid, cases[cid], mem0_row)


if __name__ == "__main__":
    main()
