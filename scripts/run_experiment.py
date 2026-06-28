"""CLI: run an experiment.

Usage:
    python scripts/run_experiment.py \\
        --cases data/cases/fusion_n50_s0.json \\
        --systems no_memory naive_markdown
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.runner import run_experiment


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--systems", nargs="+", required=True)
    ap.add_argument("--tag", default=None, help="output tag (default: timestamp)")
    args = ap.parse_args()

    tag = args.tag or time.strftime("%Y%m%d-%H%M%S")
    out = ROOT / "data" / "results" / f"{tag}.json"
    summary = run_experiment(Path(args.cases), args.systems, out)
    print(json.dumps(summary, indent=2))
    print(f"full results -> {out}")


if __name__ == "__main__":
    main()
