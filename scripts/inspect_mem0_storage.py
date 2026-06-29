"""For each given case, write its 5 initial facts + 1 update into a FRESH
mem0 instance and dump what got stored. Used to diagnose mem0's extraction
behaviour under update operations.

Each case uses its own isolated mem0 instance (via Mem0System's
per-instance tempdir) to avoid qdrant cross-process locking.

Usage:
    python scripts/inspect_mem0_storage.py --case-ids rewrite-0008 rewrite-0011 ...
    python scripts/inspect_mem0_storage.py --sample-misses 10
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.systems.mem0_system import Mem0System


def inspect(case: dict) -> dict:
    m = Mem0System()
    for u in case["initial_utterances"]:
        m.write("agent_a", u)
    m.write("agent_b", case["update_utterance"])
    all_mems = m._mem.get_all(filters={"user_id": m._user})
    items = all_mems.get("results", []) if isinstance(all_mems, dict) else all_mems
    stored = [it.get("memory", "?") for it in items]
    # mem0 instance will get garbage-collected; its qdrant tempdir is cleaned up by __del__
    return {
        "case_id": case["case_id"],
        "initial_fact_count": len(case["initial_facts"]),
        "stored_count": len(stored),
        "stored_memories": stored,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-ids", nargs="*", default=None)
    ap.add_argument("--sample-misses", type=int, default=None,
                    help="auto-pick this many cases where mem0 had a preservation miss")
    ap.add_argument("--cases-file", default="data/cases/rewrite_n200_s0.json")
    ap.add_argument("--results-file", default="data/results/rewrite-n200.json")
    args = ap.parse_args()

    cases = {c["case_id"]: c for c in json.loads(Path(args.cases_file).read_text())}

    if args.sample_misses:
        results = json.loads(Path(args.results_file).read_text())
        chosen = []
        for r in results["rows"]:
            if r["system"] != "mem0" or r.get("error"):
                continue
            n_pres_miss = sum(
                1 for p in r["per_fact"]["per_probe"]
                if p["kind"] == "preserved" and not p["hit"]
            )
            if n_pres_miss >= 1:
                chosen.append(r["case_id"])
            if len(chosen) >= args.sample_misses:
                break
        case_ids = chosen
    else:
        case_ids = args.case_ids or []

    if not case_ids:
        print("No case ids to inspect. Use --case-ids or --sample-misses.")
        return

    print(f"Inspecting {len(case_ids)} cases...\n")
    dropped_total = 0
    for cid in case_ids:
        case = cases[cid]
        old, new = case["update_old_value"], case["update_new_value"]
        cat = case["update_category"]
        print(f"=== {cid}: update {cat} {old} -> {new} ===")
        print(f"  user update utterance: {case['update_utterance']!r}")
        t0 = time.time()
        info = inspect(case)
        dt = time.time() - t0
        print(f"  stored {info['stored_count']}/{info['initial_fact_count'] + 1} expected memories ({dt:.1f}s):")
        for s in info["stored_memories"]:
            print(f"    - {s!r}")
        dropped = (info["initial_fact_count"] + 1) - info["stored_count"]
        dropped_total += max(dropped, 0)
        print()

    print(f"Total memories dropped across {len(case_ids)} cases: {dropped_total}")


if __name__ == "__main__":
    main()
