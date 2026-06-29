"""Run one fusion case end-to-end against one memory system.

Flow per case:
  1. system.reset()
  2. for each A utterance: system.write("agent_a", utterance)
  3. for each B utterance: system.write("agent_b", utterance)
  4. context = system.read("agent_c", probe_question)
  5. agent_c answers using context, via DeepSeek
  6. judge.fusion_score(answer, ground_truth)

Per-case errors are caught and recorded so one failure doesn't kill an
n=100 run. Progress is printed per case so a long run isn't a black box.
"""
import json
import sys
import traceback
from pathlib import Path
from .agent import chat
from .judge import fusion_score, rewrite_score_per_fact, rewrite_score_aggregate
from .systems import REGISTRY


AGENT_C_SYSTEM = (
    "You are agent C. Answer the user's question using ONLY the memory context "
    "provided. If the context is empty or doesn't contain a fact, say 'unknown' "
    "for that fact. Be concise — one item per category, no extra commentary."
)


def _run_one(case: dict, system) -> dict:
    system.reset()
    for u in case["a_utterances"]: system.write("agent_a", u)
    for u in case["b_utterances"]: system.write("agent_b", u)

    context = system.read("agent_c", case["probe_question"])
    user_msg = (
        f"Memory context:\n{context if context else '(empty)'}\n\n"
        f"Question: {case['probe_question']}"
    )
    answer = chat(AGENT_C_SYSTEM, user_msg)
    score = fusion_score(answer, case["ground_truth_facts"])

    return {
        "case_id": case["case_id"],
        "context_len_chars": len(context),
        "answer": answer,
        "score": score,
    }


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def run_experiment(cases_path: Path, system_names: list[str], out_path: Path) -> dict:
    cases = json.loads(cases_path.read_text())
    summary = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for sys_name in system_names:
        _log(f"\n=== {sys_name} ({len(cases)} cases) ===")
        system = REGISTRY[sys_name]()
        recalls = []
        errors = 0
        for i, case in enumerate(cases, 1):
            try:
                row = _run_one(case, system)
                row["system"] = sys_name
                row["error"] = None
                recalls.append(row["score"]["recall"])
                _log(f"  [{sys_name} {i}/{len(cases)}] {case['case_id']} recall={row['score']['recall']:.2f}")
            except Exception as e:
                errors += 1
                row = {
                    "case_id": case["case_id"],
                    "system": sys_name,
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(),
                    "score": {"recall": None, "hits": [], "misses": case["ground_truth_facts"]},
                }
                _log(f"  [{sys_name} {i}/{len(cases)}] {case['case_id']} ERROR: {type(e).__name__}: {e}")
            all_rows.append(row)

        summary[sys_name] = {
            "n_total": len(cases),
            "n_scored": len(recalls),
            "n_errors": errors,
            "mean_recall": sum(recalls) / len(recalls) if recalls else 0.0,
        }

    out_path.write_text(json.dumps({"summary": summary, "rows": all_rows}, indent=2))
    return summary


# ---------------------------------------------------------------------------
# Rewrite-preservation task
# ---------------------------------------------------------------------------

PER_FACT_PROBE_SYSTEM = (
    "You are an assistant answering questions about a person. Use ONLY the "
    "memory context provided. If the context doesn't specify a value, say "
    "'unknown'. Be concise — one short phrase, no extra commentary."
)

AGGREGATE_PROBE_SYSTEM = (
    "You are an assistant answering questions about a person. Use ONLY the "
    "memory context provided. For each category in the question, list the "
    "specific value. If the context doesn't specify a value for a category, "
    "say 'unknown' for that category. One item per category, no extra commentary."
)


def _run_rewrite_one(case: dict, system) -> dict:
    """Run one rewrite case end-to-end. Both per-fact and aggregate probes are
    evaluated; per-fact issues N separate queries, aggregate issues 1."""
    system.reset()
    # Phase 1: initial writes by agent_a.
    for u in case["initial_utterances"]:
        system.write("agent_a", u)
    # Phase 2: the update — attributed to agent_b to keep it multi-agent in
    # shape, but with a single LLM the only thing that matters is that the
    # write lands as a distinct event.
    system.write("agent_b", case["update_utterance"])

    # Phase 3a: per-fact probes — query the memory system once per fact.
    per_fact_answers = []
    for probe in case["per_fact_probes"]:
        ctx = system.read("agent_c", probe["question"])
        user_msg = (
            f"Memory context:\n{ctx if ctx else '(empty)'}\n\n"
            f"Question: {probe['question']}"
        )
        ans = chat(PER_FACT_PROBE_SYSTEM, user_msg)
        per_fact_answers.append({
            "category": probe["category"],
            "expected": probe["expected"],
            "kind": probe["kind"],
            "answer": ans,
            "context_len_chars": len(ctx),
        })
    per_fact_result = rewrite_score_per_fact(per_fact_answers)

    # Phase 3b: aggregate probe — one query for everything.
    agg = case["aggregate_probe"]
    ctx_agg = system.read("agent_c", agg["question"])
    user_msg_agg = (
        f"Memory context:\n{ctx_agg if ctx_agg else '(empty)'}\n\n"
        f"Question: {agg['question']}"
    )
    ans_agg = chat(AGGREGATE_PROBE_SYSTEM, user_msg_agg)
    agg_result = rewrite_score_aggregate(
        ans_agg,
        agg["expected_by_category"],
        case["update_category"],
    )

    return {
        "case_id": case["case_id"],
        "per_fact": per_fact_result,
        "aggregate": {**agg_result, "answer": ans_agg, "context_len_chars": len(ctx_agg)},
    }


def run_rewrite_experiment(cases_path: Path, system_names: list[str], out_path: Path) -> dict:
    cases = json.loads(cases_path.read_text())
    summary = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for sys_name in system_names:
        _log(f"\n=== {sys_name} ({len(cases)} cases) ===")
        system = REGISTRY[sys_name]()
        per_fact_update = []
        per_fact_preservation = []
        agg_update = []
        agg_preservation = []
        errors = 0

        for i, case in enumerate(cases, 1):
            try:
                row = _run_rewrite_one(case, system)
                row["system"] = sys_name
                row["error"] = None
                pf = row["per_fact"]
                ag = row["aggregate"]
                per_fact_update.append(pf["update_correct"])
                per_fact_preservation.append(pf["preservation_rate"])
                agg_update.append(ag["update_correct"])
                agg_preservation.append(ag["preservation_rate"])
                _log(
                    f"  [{sys_name} {i}/{len(cases)}] {case['case_id']} "
                    f"per_fact upd={pf['update_correct']} pres={pf['preservation_rate']:.2f} | "
                    f"agg upd={ag['update_correct']} pres={ag['preservation_rate']:.2f}"
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
            "n_scored": len(per_fact_update),
            "n_errors": errors,
            "per_fact": {
                "update_correct_rate": _mean(per_fact_update),
                "preservation_rate": _mean(per_fact_preservation),
            },
            "aggregate": {
                "update_correct_rate": _mean(agg_update),
                "preservation_rate": _mean(agg_preservation),
            },
        }

    out_path.write_text(json.dumps({"summary": summary, "rows": all_rows}, indent=2))
    return summary
