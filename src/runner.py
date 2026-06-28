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
from .judge import fusion_score
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
