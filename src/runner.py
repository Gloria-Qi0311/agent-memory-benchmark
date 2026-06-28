"""Run one fusion case end-to-end against one memory system.

Flow per case:
  1. system.reset()
  2. for each A utterance: system.write("agent_a", utterance)
  3. for each B utterance: system.write("agent_b", utterance)
  4. context = system.read("agent_c", probe_question)
  5. agent_c answers using context, via DeepSeek
  6. judge.fusion_score(answer, ground_truth)
"""
import json
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


def run_experiment(cases_path: Path, system_names: list[str], out_path: Path) -> dict:
    cases = json.loads(cases_path.read_text())
    summary = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for sys_name in system_names:
        system = REGISTRY[sys_name]()
        recalls = []
        for case in cases:
            row = _run_one(case, system)
            row["system"] = sys_name
            all_rows.append(row)
            recalls.append(row["score"]["recall"])
        summary[sys_name] = {
            "n": len(recalls),
            "mean_recall": sum(recalls) / len(recalls) if recalls else 0.0,
        }

    out_path.write_text(json.dumps({"summary": summary, "rows": all_rows}, indent=2))
    return summary
