"""Re-score stored T2 answers without calling any LLM or memory system.

The source result rows retain every reader answer. This script joins rows to
their committed cases, validates the case ground truth, recomputes all three
metrics with the current judge, and writes a reproducible corrected result.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cases.compound_update import validate_case
from src.judge import compound_update_score


def _summary(rows: list[dict]) -> dict:
    systems: dict[str, dict] = {}
    for row in rows:
        acc = systems.setdefault(row["system"], {
            "n_total": 0, "n_errors": 0, "update": [], "confusion": [], "collateral": [],
        })
        acc["n_total"] += 1
        if row.get("error"):
            acc["n_errors"] += 1
            continue
        acc["update"].append(row["score"]["update_recall"])
        acc["confusion"].append(row["score"]["no_confusion"])
        acc["collateral"].append(row["score"]["no_collateral"])

    result = {}
    for system, acc in systems.items():
        mean = lambda values: sum(values) / len(values) if values else 0.0
        result[system] = {
            "n_total": acc["n_total"],
            "n_scored": len(acc["update"]),
            "n_errors": acc["n_errors"],
            "update_recall": mean(acc["update"]),
            "no_confusion": mean(acc["confusion"]),
            "no_collateral": mean(acc["collateral"]),
        }
    return result


def rescore(
    results_path: Path,
    case_paths: list[Path],
    invalid_systems: list[str] | None = None,
) -> dict:
    source = json.loads(results_path.read_text(encoding="utf-8"))
    cases = {}
    invalid_cases = {}
    for path in case_paths:
        for case in json.loads(path.read_text(encoding="utf-8")):
            if case["case_id"] in cases:
                raise ValueError(f"duplicate case_id: {case['case_id']}")
            cases[case["case_id"]] = case
            try:
                validate_case(case)
            except ValueError as exc:
                invalid_cases[case["case_id"]] = str(exc)

    rows = []
    changed_probes = 0
    excluded_rows = 0
    for original in source["rows"]:
        if original["case_id"] in invalid_cases:
            excluded_rows += 1
            continue
        row = dict(original)
        if not row.get("error"):
            case = cases.get(row["case_id"])
            if case is None:
                raise ValueError(f"missing case for result row: {row['case_id']}")
            old_per_probe = row["score"]["per_probe"]
            probe_answers = [
                {key: probe[key] for key in (
                    "key", "kind", "expected", "answer", "context_len_chars"
                ) if key in probe}
                for probe in old_per_probe
            ]
            new_score = compound_update_score(probe_answers, case["initial_facts"])
            changed_probes += sum(
                old.get("hit") != new.get("hit")
                for old, new in zip(old_per_probe, new_score["per_probe"])
            )
            row["score"] = new_score
        rows.append(row)

    return {
        "metadata": {
            **source.get("metadata", {}),
            "rescored_from": str(results_path),
            "case_files": [str(path) for path in case_paths],
            "judge": "t2-exact-v4-token-boundary-plus-authored-aliases",
            "llm_calls": 0,
            "changed_probe_judgments": (
                source.get("metadata", {}).get("changed_probe_judgments", 0)
                + changed_probes
            ),
            "excluded_case_ids": sorted(invalid_cases),
            "exclusion_reasons": invalid_cases,
            "excluded_result_rows": (
                source.get("metadata", {}).get("excluded_result_rows", 0)
                + excluded_rows
            ),
            "known_invalid_systems": sorted(set(
                source.get("metadata", {}).get("known_invalid_systems", [])
                + (invalid_systems or [])
            )),
            "invalid_system_reason": (
                "Historical mem0 rows were produced before full reset of "
                "mem0's recent-message SQLite state between T2 cases. They "
                "require an isolated rerun and are not publishable scores."
                if "mem0" in (invalid_systems or [])
                or "mem0" in source.get("metadata", {}).get("known_invalid_systems", [])
                else None
            ),
        },
        "summary": _summary(rows),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--invalidate-system", action="append", default=[])
    args = parser.parse_args()
    result = rescore(
        Path(args.results),
        [Path(path) for path in args.cases],
        invalid_systems=args.invalidate_system,
    )
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metadata": result["metadata"], "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
