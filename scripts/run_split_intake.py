"""CLI: run a T4 (split intake) experiment.

Usage:
    python scripts/run_split_intake.py \\
        --cases data/cases/split_intake_n100_s100.json \\
        --systems no_memory naive_markdown pure_vector amh mem0 \\
        --tag t4-prod-n100
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.runner import run_split_intake_experiment


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--systems", nargs="+", required=True)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    tag = args.tag or f"t4-{time.strftime('%Y%m%d-%H%M%S')}"
    out = ROOT / "data" / "results" / f"{tag}.json"
    summary = run_split_intake_experiment(Path(args.cases), args.systems, out)
    print(json.dumps(summary, indent=2))
    print(f"full results -> {out}")


if __name__ == "__main__":
    main()
