"""CLI: generate cases for a task.

Usage:
    python scripts/generate_cases.py --task fusion --n 50
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cases import fusion, rewrite


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["fusion", "rewrite"], default="fusion")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--num-facts", type=int, default=None,
                    help="rewrite task only: number of initial facts (default 5)")
    args = ap.parse_args()

    out = ROOT / "data" / "cases" / f"{args.task}_n{args.n}_s{args.seed}.json"
    if args.task == "fusion":
        fusion.generate(args.n, out, args.seed)
    elif args.task == "rewrite":
        kwargs = {}
        if args.num_facts is not None:
            kwargs["num_facts"] = args.num_facts
        rewrite.generate(args.n, out, args.seed, **kwargs)
    print(f"wrote {args.n} cases -> {out}")


if __name__ == "__main__":
    main()
