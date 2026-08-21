"""Check that merge cases require evidence from both writer agents."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import chat


SYSTEM = """You are checking whether a preference benchmark case truly requires merging evidence.
Use only the preference evidence, current task, and candidates provided. Choose A, B, or C only if the
available preference evidence makes one candidate uniquely better. If two or more candidates remain
equally compatible, or no preference evidence is provided, choose UNKNOWN.
Return JSON only, without Markdown: {"choice":"A|B|C|UNKNOWN","reason":"one short reason"}"""

CHOICE_RE = re.compile(r"\b(UNKNOWN|[ABC])\b", re.IGNORECASE)


def _parse(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        choice = str(json.loads(cleaned)["choice"]).upper()
    except (json.JSONDecodeError, KeyError, TypeError):
        match = CHOICE_RE.search(cleaned)
        if not match:
            raise ValueError(f"cannot parse choice: {raw!r}")
        choice = match.group(1).upper()
    if choice not in {"A", "B", "C", "UNKNOWN"}:
        raise ValueError(f"invalid choice: {choice}")
    return choice


def _rotate(items: list[dict], trial: int) -> list[dict]:
    offset = trial % len(items)
    return items[offset:] + items[:offset]


def _prompt(case: dict, evidence: list[str], candidates: list[dict]) -> str:
    evidence_text = "\n".join(f"- {item}" for item in evidence) if evidence else "(none)"
    candidate_text = "\n".join(
        f"{candidate['id']}: {candidate['description']}" for candidate in candidates
    )
    return (
        f"Preference evidence:\n{evidence_text}\n\n"
        f"Current task:\n{case['decision']['task']}\n\n"
        f"Candidates:\n{candidate_text}"
    )


def run(cases_path: Path, out_path: Path, repeats: int = 3) -> dict:
    cases = [
        case for case in json.loads(cases_path.read_text(encoding="utf-8"))
        if case["layer"] == "diagnostic"
        and case["primary_capability"] == "cross_agent_merge"
    ]
    rows = []
    for case in cases:
        conditions = [
            ("no_history", []),
            ("writer_1_only", [case["writes"][0]["utterance"]]),
            ("writer_2_only", [case["writes"][1]["utterance"]]),
            ("all_writers", [write["utterance"] for write in case["writes"]]),
        ]
        for condition, evidence in conditions:
            for trial in range(repeats):
                candidates = _rotate(case["decision"]["candidates"], trial)
                target = case["ground_truth"]["expected_choice"]
                expected = target if condition == "all_writers" else "NOT_TARGET"
                try:
                    raw = chat(SYSTEM, _prompt(case, evidence, candidates), temperature=0.0)
                    choice = _parse(raw)
                    error = None
                    if condition == "no_history":
                        passed = choice == "UNKNOWN"
                    elif condition == "all_writers":
                        passed = choice == target
                    else:
                        passed = choice != target
                except Exception as exc:
                    raw = None
                    choice = None
                    passed = False
                    error = f"{type(exc).__name__}: {exc}"
                rows.append({
                    "case_id": case["case_id"],
                    "condition": condition,
                    "trial": trial + 1,
                    "candidate_order": [candidate["id"] for candidate in candidates],
                    "choice": choice,
                    "expected_choice": expected,
                    "passed": passed,
                    "raw_response": raw,
                    "error": error,
                })
                print(
                    f"{case['case_id']} {condition} trial={trial + 1} "
                    f"choice={choice} expected={expected} error={error}",
                    flush=True,
                )
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(
                    json.dumps({"metadata": {"status": "checkpoint"}, "rows": rows}, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

    condition_summaries = []
    for case in cases:
        case_rows = [row for row in rows if row["case_id"] == case["case_id"]]
        target = case["ground_truth"]["expected_choice"]
        for condition in ("no_history", "writer_1_only", "writer_2_only", "all_writers"):
            subset = [row for row in case_rows if row["condition"] == condition]
            scored = [row for row in subset if not row["error"]]
            target_rate = sum(row["choice"] == target for row in scored) / len(scored) if scored else 0.0
            unknown_rate = sum(row["choice"] == "UNKNOWN" for row in scored) / len(scored) if scored else 0.0
            if condition == "no_history":
                passed = len(scored) == repeats and unknown_rate == 1.0
            elif condition == "all_writers":
                passed = len(scored) == repeats and target_rate >= 2 / 3
            else:
                passed = len(scored) == repeats and target_rate < 1.0
            condition_summaries.append({
                "case_id": case["case_id"],
                "condition": condition,
                "target_choice": target,
                "target_choice_rate": target_rate,
                "unknown_rate": unknown_rate,
                "passed": passed,
                "n_scored": len(scored),
                "n_errors": len(subset) - len(scored),
            })

    result = {
        "metadata": {
            "check": "preference_merge_ablation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cases_path": str(cases_path),
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            "temperature": 0.0,
            "repeats": repeats,
            "n_cases": len(cases),
            "n_api_calls": len(rows),
        },
        "summary": {
            "conditions_passed": sum(item["passed"] for item in condition_summaries),
            "conditions_total": len(condition_summaries),
            "all_conditions_passed": all(item["passed"] for item in condition_summaries),
            "n_errors": sum(1 for row in rows if row["error"]),
        },
        "condition_summaries": condition_summaries,
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases", default=str(ROOT / "data" / "cases" / "preference_smoke_n12.json")
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()
    tag = args.tag or f"preference-merge-ablation-{time.strftime('%Y%m%d-%H%M%S')}"
    out = ROOT / "data" / "results" / f"{tag}.json"
    result = run(Path(args.cases), out, repeats=args.repeats)
    print(json.dumps(result["summary"], indent=2))
    print(f"full results -> {out}")


if __name__ == "__main__":
    main()
