"""CLI: run a T2 (compound update) experiment.

Usage:
    python scripts/run_compound_update.py \\
        --cases data/cases/compound_update_n10_s0.json \\
        --systems no_memory naive_markdown pure_vector amh mem0 \\
        --tag t2-smoke-n10
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.runner import run_compound_update_experiment


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--systems", nargs="+", required=True)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    tag = args.tag or f"t2-{time.strftime('%Y%m%d-%H%M%S')}"
    out = ROOT / "data" / "results" / f"{tag}.json"
    summary = run_compound_update_experiment(Path(args.cases), args.systems, out)
    print(json.dumps(summary, indent=2))
    print(f"full results -> {out}")


if __name__ == "__main__":
    main()
