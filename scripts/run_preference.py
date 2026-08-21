"""CLI: run one Preference Track experiment over selected memory systems."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.runner import run_preference_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        default=str(ROOT / "data" / "cases" / "preference_pilot_n30.json"),
    )
    parser.add_argument(
        "--systems",
        nargs="+",
        default=["naive_markdown", "amh", "mem0"],
    )
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()

    tag = args.tag or f"preference-pilot-{time.strftime('%Y%m%d-%H%M%S')}"
    out = ROOT / "data" / "results" / f"{tag}.json"
    summary = run_preference_experiment(Path(args.cases), args.systems, out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"full results -> {out}")


if __name__ == "__main__":
    main()
