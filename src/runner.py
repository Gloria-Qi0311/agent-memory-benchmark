"""Per-task experiment runners.

Each task has its own runner function (write → read → judge per case)
because the schemas, probe shapes, and metrics differ. Shared helpers
live here; task-specific functions are added as tasks are built.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
import os
import re
import sys
import time
import traceback
from pathlib import Path

from .agent import chat
from .judge import (
    split_intake_score_per_detail,
    split_intake_score_aggregate,
    compound_update_score,
)
from .systems import REGISTRY

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


# ---------------------------------------------------------------------------
# Preference Track v0
# ---------------------------------------------------------------------------

PREFERENCE_DECISION_SYSTEM = (
    "You are an assistant choosing an option for a user. Use only the shared memory context, "
    "current task, and candidate information provided. The memory may contain stable preferences, "
    "older preferences superseded by explicit updates, and temporary requirements that applied only "
    "to a past task. Use only information that is currently applicable. Within the same scope, a newer "
    "explicit update overrides an older preference, and a past one-off requirement must not be generalized "
    "to a new task. Even if the context is incomplete, choose the option that best fits the available "
    "information. Return JSON only, without Markdown: "
    "{\"choice\":\"A|B|C\",\"reason\":\"one short reason\"}"
)

_PREFERENCE_CHOICE_RE = re.compile(r'\b([ABC])\b', re.IGNORECASE)


def _parse_preference_decision(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE
        )
    try:
        parsed = json.loads(cleaned)
        choice = str(parsed["choice"]).upper()
        reason = str(parsed.get("reason", "")).strip()
    except (json.JSONDecodeError, KeyError, TypeError):
        match = _PREFERENCE_CHOICE_RE.search(cleaned)
        if not match:
            raise ValueError(f"cannot parse preference choice: {raw!r}")
        choice = match.group(1).upper()
        reason = cleaned
    if choice not in {"A", "B", "C"}:
        raise ValueError(f"invalid preference choice: {choice!r}")
    return {"choice": choice, "reason": reason}


def _preference_user_message(case: dict, context: str) -> str:
    decision = case["decision"]
    candidates = "\n".join(
        f"{candidate['id']}: {candidate['description']}"
        for candidate in decision["candidates"]
    )
    return (
        f"Shared memory context:\n{context if context else '(empty)'}\n\n"
        f"Current task:\n{decision['task']}\n\n"
        f"Candidates:\n{candidates}"
    )


def _run_preference_one(case: dict, system_name: str) -> dict:
    """Run one isolated Preference Track case from write through decision."""
    system = REGISTRY[system_name]()
    write_events = []
    started = time.perf_counter()
    try:
        for write in case["writes"]:
            write_started = time.perf_counter()
            system.write(write["agent_id"], write["utterance"])
            write_events.append({
                "order": write["order"],
                "agent_id": write["agent_id"],
                "utterance": write["utterance"],
                "elapsed_seconds": time.perf_counter() - write_started,
            })

        snapshot_started = time.perf_counter()
        try:
            memory_snapshot = system.debug_snapshot()
            snapshot_error = None
        except Exception as exc:
            memory_snapshot = None
            snapshot_error = f"{type(exc).__name__}: {exc}"
        snapshot_seconds = time.perf_counter() - snapshot_started
        try:
            native_write_results = system.debug_write_results()
        except Exception as exc:
            native_write_results = None
            if snapshot_error is None:
                snapshot_error = f"write-result inspection failed: {type(exc).__name__}: {exc}"
        write_pipeline_warning = None
        if system_name == "mem0" and not memory_snapshot:
            write_pipeline_warning = (
                "mem0 snapshot is empty after non-empty writes; internal extraction "
                "may have failed without raising to the adapter"
            )

        query = case["decision"]["memory_query"]
        read_started = time.perf_counter()
        context = system.read("agent_d", query)
        read_seconds = time.perf_counter() - read_started

        decision_started = time.perf_counter()
        raw = chat(
            PREFERENCE_DECISION_SYSTEM,
            _preference_user_message(case, context),
            temperature=0.0,
        )
        decision_seconds = time.perf_counter() - decision_started
        parsed = _parse_preference_decision(raw)
        expected = case["ground_truth"]["expected_choice"]

        return {
            "case_id": case["case_id"],
            "pair_id": case["pair_id"],
            "layer": case["layer"],
            "primary_capability": case["primary_capability"],
            "scenario": case["scenario"],
            "system": system_name,
            "writes": write_events,
            "memory_snapshot": memory_snapshot,
            "memory_snapshot_error": snapshot_error,
            "native_write_results": native_write_results,
            "write_pipeline_warning": write_pipeline_warning,
            "memory_snapshot_seconds": snapshot_seconds,
            "query": query,
            "retrieved_context": context,
            "context_chars": len(context),
            "read_seconds": read_seconds,
            "decision_raw_output": raw,
            "choice": parsed["choice"],
            "reason": parsed["reason"],
            "expected_choice": expected,
            "correct": parsed["choice"] == expected,
            "decision_seconds": decision_seconds,
            "total_seconds": time.perf_counter() - started,
            "error": None,
        }
    finally:
        system.close()


def _preference_summary(cases: list[dict], rows: list[dict]) -> dict:
    summary = {}
    for system_name in sorted({row["system"] for row in rows}):
        system_rows = [row for row in rows if row["system"] == system_name]
        scored = [row for row in system_rows if row.get("error") is None]

        capability = {}
        for name in sorted({row["primary_capability"] for row in scored}):
            subset = [row for row in scored if row["primary_capability"] == name]
            capability[name] = sum(row["correct"] for row in subset) / len(subset)

        pair_rows: dict[str, list[dict]] = defaultdict(list)
        for row in scored:
            if row["pair_id"]:
                pair_rows[row["pair_id"]].append(row)
        pair_successes = [
            len(pair) == 2 and all(row["correct"] for row in pair)
            for pair in pair_rows.values()
        ]

        summary[system_name] = {
            "n_total": len(system_rows),
            "n_scored": len(scored),
            "n_errors": len(system_rows) - len(scored),
            "decision_accuracy": (
                sum(row["correct"] for row in scored) / len(scored) if scored else 0.0
            ),
            "diagnostic_accuracy": (
                sum(row["correct"] for row in scored if row["layer"] == "diagnostic")
                / sum(1 for row in scored if row["layer"] == "diagnostic")
                if any(row["layer"] == "diagnostic" for row in scored) else 0.0
            ),
            "composite_accuracy": (
                sum(row["correct"] for row in scored if row["layer"] == "composite")
                / sum(1 for row in scored if row["layer"] == "composite")
                if any(row["layer"] == "composite" for row in scored) else 0.0
            ),
            "counterfactual_pair_success_rate": (
                sum(pair_successes) / len(pair_successes) if pair_successes else 0.0
            ),
            "accuracy_by_primary_capability": capability,
            "mean_context_chars": (
                sum(row["context_chars"] for row in scored) / len(scored) if scored else 0.0
            ),
            "mean_total_seconds": (
                sum(row["total_seconds"] for row in scored) / len(scored) if scored else 0.0
            ),
        }
    return summary


def run_preference_experiment(
    cases_path: Path,
    system_names: list[str],
    out_path: Path,
) -> dict:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    try:
        published_cases_path = str(cases_path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        published_cases_path = str(cases_path)
    unknown = [name for name in system_names if name not in REGISTRY]
    if unknown:
        raise ValueError(f"unknown memory systems: {unknown}; available={sorted(REGISTRY)}")

    rows = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for system_name in system_names:
        _log(f"\n=== {system_name} ({len(cases)} preference cases) ===")
        for index, case in enumerate(cases, 1):
            try:
                row = _run_preference_one(case, system_name)
                _log(
                    f"  [{system_name} {index}/{len(cases)}] {case['case_id']} "
                    f"choice={row['choice']} expected={row['expected_choice']} "
                    f"correct={row['correct']} ctx={row['context_chars']} chars"
                )
            except Exception as exc:
                row = {
                    "case_id": case["case_id"],
                    "pair_id": case["pair_id"],
                    "layer": case["layer"],
                    "primary_capability": case["primary_capability"],
                    "scenario": case["scenario"],
                    "system": system_name,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                }
                _log(
                    f"  [{system_name} {index}/{len(cases)}] {case['case_id']} "
                    f"ERROR: {row['error']}"
                )
            rows.append(row)
            # Keep a recoverable checkpoint even if a later API call fails.
            checkpoint = {
                "metadata": {
                    "task": "preference",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "cases_path": published_cases_path,
                    "case_set": cases_path.stem,
                    "case_count": len(cases),
                    "systems": system_names,
                    "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                    "temperature": 0.0,
                    "runs": 1,
                },
                "summary": _preference_summary(cases, rows),
                "rows": rows,
            }
            out_path.write_text(
                json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    return _preference_summary(cases, rows)
