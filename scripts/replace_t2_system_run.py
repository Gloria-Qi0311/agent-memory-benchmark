"""Replace one system's historical T2 rows with a validated rerun."""
import argparse
import json
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--replacement", required=True)
    parser.add_argument("--system", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    base_path = Path(args.base)
    replacement_path = Path(args.replacement)
    base = json.loads(base_path.read_text(encoding="utf-8"))
    replacement = json.loads(replacement_path.read_text(encoding="utf-8"))

    replacement_rows = [
        row for row in replacement["rows"] if row["system"] == args.system
    ]
    if not replacement_rows:
        raise SystemExit(f"replacement has no rows for {args.system}")
    if any(row["system"] != args.system for row in replacement["rows"]):
        raise SystemExit("replacement file contains another system")

    rows = [row for row in base["rows"] if row["system"] != args.system]
    rows.extend(replacement_rows)

    # Reuse the merge summarizer through temporary in-memory-equivalent files
    # would obscure provenance; compute the three means directly here.
    systems = {}
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

    summary = {}
    for system, acc in systems.items():
        mean = lambda values: sum(values) / len(values) if values else 0.0
        summary[system] = {
            "n_total": acc["n_total"],
            "n_scored": len(acc["update"]),
            "n_errors": acc["n_errors"],
            "update_recall": mean(acc["update"]),
            "no_confusion": mean(acc["confusion"]),
            "no_collateral": mean(acc["collateral"]),
        }

    metadata = dict(base.get("metadata", {}))
    invalid = set(metadata.get("known_invalid_systems", []))
    invalid.discard(args.system)
    metadata.update({
        "known_invalid_systems": sorted(invalid),
        "invalid_system_reason": None if not invalid else metadata.get("invalid_system_reason"),
        "replaced_system_runs": {
            **metadata.get("replaced_system_runs", {}),
            args.system: str(replacement_path),
        },
        "per_case_full_reset": {
            **metadata.get("per_case_full_reset", {}),
            args.system: True,
        },
    })
    result = {"metadata": metadata, "summary": summary, "rows": rows}
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metadata": metadata, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
