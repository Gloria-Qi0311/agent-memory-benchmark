"""CLI: generate cases for a task.

Usage:
    python scripts/generate_cases.py --task fusion --n 50
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cases import fusion


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["fusion"], default="fusion")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    out = ROOT / "data" / "cases" / f"{args.task}_n{args.n}_s{args.seed}.json"
    if args.task == "fusion":
        fusion.generate(args.n, out, args.seed)
    print(f"wrote {args.n} cases -> {out}")


if __name__ == "__main__":
    main()
