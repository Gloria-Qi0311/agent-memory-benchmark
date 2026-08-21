"""Run the Preference Track no-history case-quality check.

This is not a benchmarked memory system. It is a dataset quality gate:
the reader receives only the current task and candidates, never preference
history, retrieved context, or hidden ground truth.

Each unique decision surface is checked in two modes and three candidate
orders:

1. forced_choice: mirrors the eventual A/B/C task and exposes the reader's
   default answer when memory is absent;
2. allow_unknown: asks whether the options have an objectively unique winner.
   A balanced preference case should normally produce UNKNOWN.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import chat


FORCED_SYSTEM = """You are running a no-history baseline check for a user-preference benchmark.
You cannot see any user history or preferences and must not invent hidden preferences.
Answer using only the current task and candidate descriptions. Even if the information is insufficient,
you must choose the most reasonable default from A, B, and C.
Return JSON only, without Markdown: {"choice":"A|B|C","reason":"one short reason"}"""

UNKNOWN_SYSTEM = """You are checking whether a user-preference question leaks its answer.
You cannot see any user history or preferences and must not invent hidden preferences.
Determine whether the current task and candidates alone contain one objectively best option for nearly
all reasonable users. If the candidates have genuine trade-offs and user preferences are required,
choose UNKNOWN. Choose A, B, or C only if one candidate clearly dominates the others.
Return JSON only, without Markdown: {"choice":"A|B|C|UNKNOWN","reason":"one short reason"}"""

CHOICE_RE = re.compile(r'\b(UNKNOWN|[ABC])\b', re.IGNORECASE)


def _parse_choice(raw: str, allow_unknown: bool) -> str:
    """Extract a valid choice from JSON, tolerating fenced/plain fallbacks."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        choice = str(json.loads(cleaned)["choice"]).upper()
    except (json.JSONDecodeError, KeyError, TypeError):
        match = CHOICE_RE.search(cleaned)
        if not match:
            raise ValueError(f"cannot parse choice from response: {raw!r}")
        choice = match.group(1).upper()

    valid = {"A", "B", "C"}
    if allow_unknown:
        valid.add("UNKNOWN")
    if choice not in valid:
        raise ValueError(f"invalid choice {choice!r}; valid={sorted(valid)}")
    return choice


def _surface_id(decision: dict) -> str:
    payload = json.dumps(decision, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _rotated_candidates(candidates: list[dict], trial: int) -> list[dict]:
    offset = trial % len(candidates)
    return candidates[offset:] + candidates[:offset]


def _user_prompt(decision: dict, candidates: list[dict]) -> str:
    candidate_text = "\n".join(
        f"{candidate['id']}: {candidate['description']}" for candidate in candidates
    )
    return f"Current task:\n{decision['task']}\n\nCandidates:\n{candidate_text}"


def _run_trial(decision: dict, mode: str, trial: int) -> dict:
    candidates = _rotated_candidates(decision["candidates"], trial)
    allow_unknown = mode == "allow_unknown"
    system = UNKNOWN_SYSTEM if allow_unknown else FORCED_SYSTEM
    raw = chat(system, _user_prompt(decision, candidates), temperature=0.0)
    return {
        "mode": mode,
        "trial": trial + 1,
        "candidate_order": [candidate["id"] for candidate in candidates],
        "choice": _parse_choice(raw, allow_unknown=allow_unknown),
        "raw_response": raw,
    }


def _dominant(counter: Counter) -> tuple[str | None, float]:
    if not counter:
        return None, 0.0
    choice, count = counter.most_common(1)[0]
    return choice, count / sum(counter.values())


def run_check(cases_path: Path, out_path: Path, repeats: int = 3) -> dict:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    surfaces: dict[str, dict] = {}
    surface_cases: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        surface_id = _surface_id(case["decision"])
        surfaces.setdefault(surface_id, case["decision"])
        surface_cases[surface_id].append(case)

    rows = []
    for surface_index, (surface_id, decision) in enumerate(surfaces.items(), 1):
        print(
            f"[{surface_index}/{len(surfaces)}] surface={surface_id} "
            f"cases={[case['case_id'] for case in surface_cases[surface_id]]}",
            flush=True,
        )
        for mode in ("forced_choice", "allow_unknown"):
            for trial in range(repeats):
                try:
                    row = _run_trial(decision, mode, trial)
                    row["error"] = None
                    print(
                        f"  {mode} trial={trial + 1} "
                        f"order={row['candidate_order']} choice={row['choice']}",
                        flush=True,
                    )
                except Exception as exc:
                    row = {
                        "mode": mode,
                        "trial": trial + 1,
                        "candidate_order": [
                            candidate["id"]
                            for candidate in _rotated_candidates(decision["candidates"], trial)
                        ],
                        "choice": None,
                        "raw_response": None,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                    print(f"  {mode} trial={trial + 1} ERROR {row['error']}", flush=True)
                row["surface_id"] = surface_id
                rows.append(row)

    surface_summaries = []
    case_summaries = []
    for surface_id, decision in surfaces.items():
        surface_rows = [row for row in rows if row["surface_id"] == surface_id]
        forced = Counter(
            row["choice"] for row in surface_rows
            if row["mode"] == "forced_choice" and row["choice"]
        )
        unknown_mode = Counter(
            row["choice"] for row in surface_rows
            if row["mode"] == "allow_unknown" and row["choice"]
        )
        forced_choice, forced_share = _dominant(forced)
        non_unknown = sum(
            count for choice, count in unknown_mode.items() if choice != "UNKNOWN"
        )
        unknown_total = sum(unknown_mode.values())
        non_unknown_rate = non_unknown / unknown_total if unknown_total else 0.0
        paired = len(surface_cases[surface_id]) == 2

        if non_unknown_rate >= 2 / 3:
            quality_status = "fail_objective_winner"
        elif non_unknown_rate > 0:
            quality_status = "review_unstable_objective_winner"
        elif paired:
            quality_status = "pass_pair_controlled"
        else:
            expected = surface_cases[surface_id][0]["ground_truth"]["expected_choice"]
            if forced_choice == expected and forced_share >= 2 / 3:
                quality_status = "review_default_matches_truth"
            else:
                quality_status = "pass"

        surface_summary = {
            "surface_id": surface_id,
            "case_ids": [case["case_id"] for case in surface_cases[surface_id]],
            "paired_counterfactual": paired,
            "forced_choice_counts": dict(forced),
            "forced_dominant_choice": forced_choice,
            "forced_dominant_share": forced_share,
            "allow_unknown_counts": dict(unknown_mode),
            "allow_unknown_non_unknown_rate": non_unknown_rate,
            "quality_status": quality_status,
        }
        surface_summaries.append(surface_summary)

        for case in surface_cases[surface_id]:
            expected = case["ground_truth"]["expected_choice"]
            scored_forced = sum(forced.values())
            case_summaries.append({
                "case_id": case["case_id"],
                "surface_id": surface_id,
                "layer": case["layer"],
                "expected_choice": expected,
                "forced_choice_hit_rate": forced.get(expected, 0) / scored_forced if scored_forced else 0.0,
                "quality_status": quality_status,
            })

    status_counts = Counter(item["quality_status"] for item in surface_summaries)
    diagnostic_hits = [
        item["forced_choice_hit_rate"]
        for item in case_summaries
        if item["layer"] == "diagnostic"
    ]
    composite_hits = [
        item["forced_choice_hit_rate"]
        for item in case_summaries
        if item["layer"] == "composite"
    ]
    all_hits = diagnostic_hits + composite_hits
    unknown_rows = [row for row in rows if row["mode"] == "allow_unknown"]

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    result = {
        "metadata": {
            "check": "preference_no_history_quality_gate",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cases_path": str(cases_path),
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            "temperature": 0.0,
            "repeats_per_mode": repeats,
            "n_cases": len(cases),
            "n_unique_decision_surfaces": len(surfaces),
            "n_api_calls": len(rows),
        },
        "summary": {
            "surface_status_counts": dict(status_counts),
            "n_errors": sum(1 for row in rows if row["error"]),
            "diagnostic_forced_choice_hit_rate": _mean(diagnostic_hits),
            "composite_forced_choice_hit_rate": _mean(composite_hits),
            "overall_forced_choice_hit_rate": _mean(all_hits),
            "allow_unknown_abstention_rate": (
                sum(1 for row in unknown_rows if row["choice"] == "UNKNOWN")
                / len(unknown_rows)
                if unknown_rows else 0.0
            ),
        },
        "surface_summaries": surface_summaries,
        "case_summaries": case_summaries,
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        default=str(ROOT / "data" / "cases" / "preference_smoke_n12.json"),
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    tag = args.tag or f"preference-no-history-{time.strftime('%Y%m%d-%H%M%S')}"
    out_path = ROOT / "data" / "results" / f"{tag}.json"
    result = run_check(Path(args.cases), out_path, repeats=args.repeats)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"full results -> {out_path}")


if __name__ == "__main__":
    main()
