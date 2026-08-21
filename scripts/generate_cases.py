"""CLI: generate cases for a task.

Usage:
    python scripts/generate_cases.py --task split_intake --n 100 --seed 100
    python scripts/generate_cases.py --task compound_update --n 10 --seed 0
    python scripts/generate_cases.py --task preference_smoke
    python scripts/generate_cases.py --task preference_pilot
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cases import split_intake, compound_update, preference, preference_pilot


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--task",
        choices=["split_intake", "compound_update", "preference_smoke", "preference_pilot"],
        default="split_intake",
    )
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.task == "preference_smoke":
        out = ROOT / "data" / "cases" / "preference_smoke_n12.json"
        preference.generate_smoke(out)
        print(f"wrote 12 curated cases -> {out}")
        return

    if args.task == "preference_pilot":
        out = ROOT / "data" / "cases" / "preference_pilot_n30.json"
        preference_pilot.generate_pilot(out)
        review = ROOT / "docs" / "v1" / "preference_pilot_case_review.md"
        preference_pilot.generate_review(review)
        print(f"wrote 30 curated cases -> {out}")
        print(f"wrote product review -> {review}")
        return

    out = ROOT / "data" / "cases" / f"{args.task}_n{args.n}_s{args.seed}.json"
    if args.task == "split_intake":
        split_intake.generate(args.n, out, args.seed)
    elif args.task == "compound_update":
        compound_update.generate(args.n, out, args.seed)
    print(f"wrote {args.n} cases -> {out}")


if __name__ == "__main__":
    main()
