"""Per-task experiment runners.

Each task has its own runner function (write → read → judge per case)
because the schemas, probe shapes, and metrics differ. Shared helpers
live here; task-specific functions are added as tasks are built.
"""
import json
import sys
import traceback
from pathlib import Path

from .agent import chat
from .judge import (
    split_intake_score_per_detail,
    split_intake_score_aggregate,
    compound_update_score,
)
from .systems import REGISTRY


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# T4 — split intake
# ---------------------------------------------------------------------------

PER_DETAIL_PROBE_SYSTEM = (
    "You are an assistant answering a single question about a person. Use "
    "ONLY the memory context provided — do not add information from outside. "
    "If the context doesn't contain the answer, say 'unknown'. Be concise: "
    "one short phrase, no extra commentary."
)

AGGREGATE_PROBE_SYSTEM = (
    "You are an assistant answering a question about a person. Use ONLY the "
    "memory context provided — do not add information from outside. The "
    "question asks about several categories at once. For each category, "
    "give the specific value. If the context doesn't have a value for a "
    "category, say 'unknown' for that category. One item per category, no "
    "extra commentary."
)


def _run_split_intake_one(case: dict, system) -> dict:
    """Run one T4 case end-to-end.

    Flow:
      1. system.reset()
      2. system.write("agent_a", user_statement)  # one shot — the memory
         system decides how to decompose internally
      3. for each per-detail probe: system.read + LLM answer
      4. for the aggregate probe: system.read + LLM answer
      5. judge both
    """
    system.reset()
    system.write("agent_a", case["user_statement"])

    # Phase 1: per-detail probes
    per_detail_answers = []
    for probe in case["per_detail_probes"]:
        ctx = system.read("agent_c", probe["question"])
        user_msg = (
            f"Memory context:\n{ctx if ctx else '(empty)'}\n\n"
            f"Question: {probe['question']}"
        )
        ans = chat(PER_DETAIL_PROBE_SYSTEM, user_msg)
        per_detail_answers.append({
            "key": probe["key"],
            "expected": probe["expected"],
            "answer": ans,
            "context_len_chars": len(ctx),
        })
    per_detail = split_intake_score_per_detail(per_detail_answers)

    # Phase 2: aggregate probe
    agg = case["aggregate_probe"]
    ctx_agg = system.read("agent_c", agg["question"])
    user_msg_agg = (
        f"Memory context:\n{ctx_agg if ctx_agg else '(empty)'}\n\n"
        f"Question: {agg['question']}"
    )
    ans_agg = chat(AGGREGATE_PROBE_SYSTEM, user_msg_agg)
    aggregate = split_intake_score_aggregate(ans_agg, agg["expected_by_key"])

    return {
        "case_id": case["case_id"],
        "scenario": case.get("scenario"),
        "per_detail": per_detail,
        "aggregate": {**aggregate, "answer": ans_agg, "context_len_chars": len(ctx_agg)},
    }


def run_split_intake_experiment(
    cases_path: Path,
    system_names: list[str],
    out_path: Path,
) -> dict:
    cases = json.loads(cases_path.read_text())
    summary = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for sys_name in system_names:
        _log(f"\n=== {sys_name} ({len(cases)} cases) ===")
        system = REGISTRY[sys_name]()
        per_detail_recalls = []
        agg_recalls = []
        errors = 0

        for i, case in enumerate(cases, 1):
            try:
                row = _run_split_intake_one(case, system)
                row["system"] = sys_name
                row["error"] = None
                per_detail_recalls.append(row["per_detail"]["recall"])
                agg_recalls.append(row["aggregate"]["recall"])
                _log(
                    f"  [{sys_name} {i}/{len(cases)}] {case['case_id']} "
                    f"per_detail={row['per_detail']['recall']:.2f} "
                    f"agg={row['aggregate']['recall']:.2f}"
                )
            except Exception as e:
                errors += 1
                row = {
                    "case_id": case["case_id"],
                    "system": sys_name,
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(),
                }
                _log(f"  [{sys_name} {i}/{len(cases)}] {case['case_id']} ERROR: {type(e).__name__}: {e}")
            all_rows.append(row)

        def _mean(xs): return sum(xs) / len(xs) if xs else 0.0
        summary[sys_name] = {
            "n_total": len(cases),
            "n_scored": len(per_detail_recalls),
            "n_errors": errors,
            "per_detail_recall": _mean(per_detail_recalls),
            "aggregate_recall": _mean(agg_recalls),
        }

    out_path.write_text(json.dumps({"summary": summary, "rows": all_rows}, indent=2))
    return summary


# ---------------------------------------------------------------------------
# T2 — compound update
# ---------------------------------------------------------------------------

COMPOUND_UPDATE_PROBE_SYSTEM = (
    "You are an assistant answering a single question about a person. Use "
    "ONLY the memory context provided. If the context is unclear about the "
    "answer, say 'unknown'. If the context contains multiple values for the "
    "same category (e.g. an old value and a newer one), pick the most recent "
    "one. Be concise: one short phrase, no extra commentary."
)


def _run_compound_update_one(case: dict, system) -> dict:
    """Run one T2 case end-to-end.

    Flow:
      Phase 1: agent_a writes each of the N initial_utterances individually
      Phase 2: agent_b writes the single compound update_utterance
      Phase 3: agent_c asks each probe question and answers via reader LLM
    """
    system.reset()
    # Phase 1
    for utt in case["initial_utterances"]:
        system.write("agent_a", utt)
    # Phase 2
    system.write("agent_b", case["update_utterance"])

    # Phase 3
    probe_answers = []
    for probe in case["probes"]:
        ctx = system.read("agent_c", probe["question"])
        user_msg = (
            f"Memory context:\n{ctx if ctx else '(empty)'}\n\n"
            f"Question: {probe['question']}"
        )
        ans = chat(COMPOUND_UPDATE_PROBE_SYSTEM, user_msg)
        probe_answers.append({
            "key": probe["key"],
            "kind": probe["kind"],
            "expected": probe["expected"],
            "answer": ans,
            "context_len_chars": len(ctx),
        })

    score = compound_update_score(probe_answers, case["initial_facts"])

    return {
        "case_id": case["case_id"],
        "scenario": case.get("scenario"),
        "score": score,
    }


def run_compound_update_experiment(
    cases_path: Path,
    system_names: list[str],
    out_path: Path,
) -> dict:
    cases = json.loads(cases_path.read_text())
    summary = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for sys_name in system_names:
        _log(f"\n=== {sys_name} ({len(cases)} cases) ===")
        system = REGISTRY[sys_name]()
        update_recalls = []
        no_confusions = []
        no_collaterals = []
        errors = 0

        for i, case in enumerate(cases, 1):
            try:
                row = _run_compound_update_one(case, system)
                row["system"] = sys_name
                row["error"] = None
                s = row["score"]
                update_recalls.append(s["update_recall"])
                no_confusions.append(s["no_confusion"])
                no_collaterals.append(s["no_collateral"])
                _log(
                    f"  [{sys_name} {i}/{len(cases)}] {case['case_id']} "
                    f"upd_recall={s['update_recall']:.2f} "
                    f"no_conf={s['no_confusion']:.2f} "
                    f"no_coll={s['no_collateral']:.2f}"
                )
            except Exception as e:
                errors += 1
                row = {
                    "case_id": case["case_id"],
                    "system": sys_name,
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(),
                }
                _log(f"  [{sys_name} {i}/{len(cases)}] {case['case_id']} ERROR: {type(e).__name__}: {e}")
            all_rows.append(row)

        def _mean(xs): return sum(xs) / len(xs) if xs else 0.0
        summary[sys_name] = {
            "n_total": len(cases),
            "n_scored": len(update_recalls),
            "n_errors": errors,
            "update_recall": _mean(update_recalls),
            "no_confusion": _mean(no_confusions),
            "no_collateral": _mean(no_collaterals),
        }

    out_path.write_text(json.dumps({"summary": summary, "rows": all_rows}, indent=2))
    return summary
