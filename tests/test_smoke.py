"""Smoke tests — sanity-check primitives without hitting any LLM API.
Run: pytest tests/
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.judge import (
    _match,
    split_intake_score_per_detail,
    split_intake_score_aggregate,
    compound_update_score,
)
from src.systems.no_memory import NoMemory
from src.systems.naive_markdown import NaiveMarkdown
from src.systems.amh_system import AMHSystem


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

def test_match_word_boundary():
    # _match's contract: caller passes ALREADY-LOWERCASED text.
    assert _match("Go", "i'm using go on aws")
    assert not _match("Go", "i'm going to aws")
    assert _match("Python", "alex uses python")
    assert _match("Rust", "switched to rust.")


def test_no_memory_is_empty():
    m = NoMemory()
    m.write("agent_a", "something")
    assert m.read("agent_c", "?") == ""


def test_naive_markdown_roundtrip():
    m = NaiveMarkdown()
    m.write("agent_a", "Alex uses Python")
    m.write("agent_b", "Alex lives in Berlin")
    ctx = m.read("agent_c", "tell me about alex")
    assert "Python" in ctx and "Berlin" in ctx


def test_amh_write_read_roundtrip():
    """AMH is Markdown+FS-backed. Verify write -> read surfaces content
    for a keyword query, and reset wipes the store."""
    m = AMHSystem()
    m.write("agent_a", "Alex uses Python as their language.")
    m.write("agent_a", "Alex uses VSCode as their editor.")
    ctx = m.read("agent_c", "what language does Alex use")
    assert "Python" in ctx
    m.reset()
    assert m.read("agent_c", "what language does Alex use") == ""


# ---------------------------------------------------------------------------
# T4 case generator
# ---------------------------------------------------------------------------

def test_split_intake_generator_deterministic():
    from src.cases import split_intake
    # NOTE: we use a scenario_name override to avoid the LLM call inside
    # make_case() — we only check the values dict, not the rephrased text.
    # The values picker doesn't hit the LLM; only _rephrase_with_verification
    # does, and we test that path separately by inspecting committed cases.
    a = split_intake.make_case(seed=42, scenario_name="home_office")
    b = split_intake.make_case(seed=42, scenario_name="home_office")
    assert a.case_id == b.case_id
    assert a.ground_truth_details == b.ground_truth_details
    assert a.scenario == "home_office"


def test_split_intake_dev_setup_laptop_os_compat():
    """Every dev_setup case must have an OS compatible with the laptop."""
    from src.cases.split_intake import _pick_values, SCENARIOS, _LAPTOP_OS_COMPAT
    import random
    for seed in range(50):
        r = random.Random(seed)
        vals = _pick_values(r, "dev_setup", SCENARIOS["dev_setup"])
        assert vals["os"] in _LAPTOP_OS_COMPAT[vals["laptop"]], \
            f"seed={seed}: laptop={vals['laptop']} got incompatible os={vals['os']}"


def test_split_intake_travel_dates_are_chronologically_sane():
    """Every travel_plan case must use a (depart, return) pair from the
    pre-vetted same-or-adjacent-month list — no Nov->Sep madness."""
    from src.cases.split_intake import _pick_values, SCENARIOS, _TRAVEL_DATE_PAIRS
    import random
    for seed in range(50):
        r = random.Random(seed)
        vals = _pick_values(r, "travel_plan", SCENARIOS["travel_plan"])
        assert (vals["depart_date"], vals["return_date"]) in _TRAVEL_DATE_PAIRS, \
            f"seed={seed}: got date pair ({vals['depart_date']}, {vals['return_date']})"


# ---------------------------------------------------------------------------
# T4 judge
# ---------------------------------------------------------------------------

def test_split_intake_score_per_detail_full_hit():
    probes = [
        {"key": "laptop", "expected": "MacBook Pro M4 Max", "answer": "MacBook Pro M4 Max"},
        {"key": "ram",    "expected": "64GB",                "answer": "64GB of memory"},
    ]
    s = split_intake_score_per_detail(probes)
    assert s["recall"] == 1.0
    assert s["hits"] == ["laptop", "ram"]
    assert s["misses"] == []


def test_split_intake_score_per_detail_partial():
    probes = [
        {"key": "laptop", "expected": "MacBook Pro M4 Max", "answer": "MacBook Pro M4 Max"},
        {"key": "ram",    "expected": "64GB",                "answer": "unknown"},
        {"key": "ide",    "expected": "Cursor",              "answer": "VSCode"},  # wrong value
    ]
    s = split_intake_score_per_detail(probes)
    assert s["recall"] == 1 / 3
    assert s["hits"] == ["laptop"]
    assert set(s["misses"]) == {"ram", "ide"}


def test_split_intake_score_aggregate_all_present():
    expected = {"laptop": "MacBook Pro M4 Max", "ide": "Cursor", "terminal": "Ghostty"}
    answer = "Laptop: MacBook Pro M4 Max, IDE: Cursor, Terminal: Ghostty."
    s = split_intake_score_aggregate(answer, expected)
    assert s["recall"] == 1.0
    assert set(s["hits"]) == {"laptop", "ide", "terminal"}


def test_split_intake_score_aggregate_one_missing():
    expected = {"laptop": "MacBook Pro M4 Max", "ide": "Cursor", "terminal": "Ghostty"}
    # answer leaves out terminal
    answer = "Laptop: MacBook Pro M4 Max, IDE: Cursor, Terminal: unknown."
    s = split_intake_score_aggregate(answer, expected)
    assert s["recall"] == 2 / 3
    assert "terminal" in s["misses"]


def test_split_intake_score_aggregate_word_boundary():
    """A value embedded as a substring of a larger word should NOT match."""
    expected = {"language": "Go"}
    answer = "alex is going to switch languages"
    s = split_intake_score_aggregate(answer, expected)
    assert s["recall"] == 0.0
    assert s["misses"] == ["language"]


# ---------------------------------------------------------------------------
# T2 case generator
# ---------------------------------------------------------------------------

def test_compound_update_generator_deterministic():
    from src.cases import compound_update
    a = compound_update.make_case(seed=42, scenario_name="home_office")
    b = compound_update.make_case(seed=42, scenario_name="home_office")
    assert a.case_id == b.case_id
    assert a.initial_facts == b.initial_facts
    assert a.updated_facts == b.updated_facts
    assert a.update_utterance == b.update_utterance


def test_compound_update_case_shape():
    from src.cases import compound_update
    c = compound_update.make_case(seed=7, n=10, k=4)
    assert len(c.initial_facts) == 10
    assert len(c.updated_facts) == 4
    assert len(c.initial_utterances) == 10
    assert len(c.probes) == 10
    # 4 updated + 6 preserved probes
    updated = [p for p in c.probes if p["kind"] == "updated"]
    preserved = [p for p in c.probes if p["kind"] == "preserved"]
    assert len(updated) == 4
    assert len(preserved) == 6
    # Updated probes' expected is the NEW value; preserved probes' expected
    # is the initial value.
    for p in updated:
        assert p["expected"] == c.updated_facts[p["key"]]
        assert p["expected"] != c.initial_facts[p["key"]]
    for p in preserved:
        assert p["expected"] == c.initial_facts[p["key"]]


def test_compound_update_travel_dates_stay_paired():
    """If both depart_date and return_date are updated, the new pair must be a
    valid pre-vetted chronologically-sane pair (not two random dates)."""
    from src.cases import compound_update
    from src.cases.split_intake import _TRAVEL_DATE_PAIRS
    # Force travel_plan and iterate to find a case where both dates got picked
    # for update. Not every seed will do it; that's fine — we just need at
    # least one to hit and verify the constraint.
    saw_paired_update = False
    for s in range(200):
        c = compound_update.make_case(seed=s, scenario_name="travel_plan")
        if "depart_date" in c.updated_facts and "return_date" in c.updated_facts:
            saw_paired_update = True
            depart = c.updated_facts["depart_date"]
            ret = c.updated_facts["return_date"]
            assert (depart, ret) in _TRAVEL_DATE_PAIRS, \
                f"seed={s}: got invalid new date pair ({depart}, {ret})"
    assert saw_paired_update, "no seed in 0..199 produced a paired-date update; loosen or expand"


# ---------------------------------------------------------------------------
# T2 judge
# ---------------------------------------------------------------------------

def test_compound_update_score_perfect_update_and_preservation():
    """All updated probes hit new values, no old values leak, all preserved
    probes hit initial values -> all three metrics = 1.0."""
    initial = {"language": "Python", "framework": "Django", "db": "Postgres"}
    probes = [
        {"key": "language", "kind": "updated",  "expected": "TypeScript",
         "answer": "TypeScript"},
        {"key": "framework", "kind": "updated", "expected": "Next.js",
         "answer": "Next.js"},
        {"key": "db",  "kind": "preserved", "expected": "Postgres",
         "answer": "Postgres"},
    ]
    s = compound_update_score(probes, initial)
    assert s["update_recall"] == 1.0
    assert s["no_confusion"] == 1.0
    assert s["no_collateral"] == 1.0


def test_compound_update_score_old_value_leaks_hurts_no_confusion():
    """Answer mentions BOTH new and old value for an updated probe -> hit
    counts, but no_confusion is dinged."""
    initial = {"language": "Python"}
    probes = [
        {"key": "language", "kind": "updated", "expected": "TypeScript",
         "answer": "Used to be Python but now TypeScript"},
    ]
    s = compound_update_score(probes, initial)
    assert s["update_recall"] == 1.0  # new value present
    assert s["no_confusion"] == 0.0   # old value also present -> confusion


def test_compound_update_score_collateral_damage():
    """A preserved probe answered with the wrong value -> no_collateral drops."""
    initial = {"language": "Python", "db": "Postgres"}
    probes = [
        {"key": "language", "kind": "updated",   "expected": "TypeScript",
         "answer": "TypeScript"},
        {"key": "db",       "kind": "preserved", "expected": "Postgres",
         "answer": "MongoDB"},
    ]
    s = compound_update_score(probes, initial)
    assert s["update_recall"] == 1.0
    assert s["no_collateral"] == 0.0


# ---------------------------------------------------------------------------
# Preference Track v0 smoke cases
# ---------------------------------------------------------------------------

def test_preference_smoke_case_distribution():
    """The review batch is exactly the agreed 6 diagnostic + 6 composite."""
    from collections import Counter
    from src.cases.preference import smoke_cases

    cases = smoke_cases()
    assert len(cases) == 12
    assert Counter(c["layer"] for c in cases) == {
        "diagnostic": 6,
        "composite": 6,
    }
    assert Counter(
        c["primary_capability"]
        for c in cases
        if c["layer"] == "diagnostic"
    ) == {
        "cross_agent_merge": 2,
        "preference_update": 2,
        "preference_boundary": 2,
    }


def test_preference_smoke_cases_validate():
    """Every curated case satisfies the executable schema and unique-winner rule."""
    from src.cases.preference import smoke_cases, validate_case

    for case in smoke_cases():
        validate_case(case)


def test_preference_merge_cases_require_both_evidence_groups():
    from src.cases.preference import smoke_cases

    merge_cases = [
        case for case in smoke_cases()
        if case["primary_capability"] == "cross_agent_merge"
    ]
    assert len(merge_cases) == 2
    for case in merge_cases:
        candidates = case["decision"]["candidates"]
        groups = case["ground_truth"]["evidence_groups"]
        assert len(groups) == 2
        for group in groups:
            scores = {
                candidate["id"]: len(set(group).intersection(candidate["attributes"]))
                for candidate in candidates
            }
            best = max(scores.values())
            assert sum(score == best for score in scores.values()) >= 2


def test_preference_utterances_are_direct_user_speech():
    """Writer inputs should look like user messages, not dataset narration."""
    from src.cases.preference import smoke_cases

    for case in smoke_cases():
        for write in case["writes"]:
            assert not write["utterance"].startswith(f'{case["persona"]}说：')


def test_preference_composite_counterfactual_pairs():
    """Each composite pair keeps the decision surface fixed but flips truth."""
    from collections import defaultdict
    from src.cases.preference import smoke_cases

    pairs = defaultdict(list)
    for case in smoke_cases():
        if case["layer"] == "composite":
            pairs[case["pair_id"]].append(case)

    assert len(pairs) == 3
    for pair_id, pair in pairs.items():
        assert pair_id
        assert len(pair) == 2
        left, right = pair
        assert left["decision"] == right["decision"]
        assert left["persona"] == right["persona"]
        assert left["ground_truth"]["expected_choice"] != right["ground_truth"]["expected_choice"]
        assert left["writes"] != right["writes"]
        # The scoped one-off event is held fixed; only the target preference
        # history changes between the two counterfactual variants.
        assert left["writes"][-1] == right["writes"][-1]


def test_preference_case_final_agent_has_no_history():
    """The decision surface contains no writer utterances or hidden truth."""
    from src.cases.preference import smoke_cases

    for case in smoke_cases():
        decision_text = str(case["decision"])
        for write in case["writes"]:
            assert write["utterance"] not in decision_text
        assert "ground_truth" not in case["decision"]


def test_preference_expected_choice_is_unique_best_match():
    """Ground truth is computed from candidate attributes, not an arbitrary label."""
    from src.cases.preference import preference_match_scores, smoke_cases

    for case in smoke_cases():
        scores = preference_match_scores(case)
        best = max(scores.values())
        winners = [candidate_id for candidate_id, score in scores.items() if score == best]
        assert winners == [case["ground_truth"]["expected_choice"]]


def test_preference_smoke_choice_positions_are_balanced():
    """The review batch must not reward a fixed A/B/C position strategy."""
    from collections import Counter
    from src.cases.preference import smoke_cases

    assert Counter(
        case["ground_truth"]["expected_choice"] for case in smoke_cases()
    ) == {"A": 4, "B": 4, "C": 4}


def test_preference_pilot_distribution_and_validation():
    from collections import Counter
    from src.cases.preference_pilot import pilot_cases

    cases = pilot_cases()
    assert len(cases) == 30
    assert Counter(case["layer"] for case in cases) == {
        "diagnostic": 12,
        "composite": 18,
    }
    assert Counter(
        case["primary_capability"]
        for case in cases
        if case["layer"] == "diagnostic"
    ) == {
        "cross_agent_merge": 4,
        "preference_update": 4,
        "preference_boundary": 4,
    }


def test_preference_pilot_has_nine_counterfactual_pairs():
    from collections import Counter
    from src.cases.preference_pilot import pilot_cases

    pair_counts = Counter(
        case["pair_id"] for case in pilot_cases() if case["pair_id"]
    )
    assert len(pair_counts) == 9
    assert set(pair_counts.values()) == {2}


def test_preference_pilot_choice_positions_are_balanced():
    from collections import Counter
    from src.cases.preference_pilot import pilot_cases

    counts = Counter(case["ground_truth"]["expected_choice"] for case in pilot_cases())
    assert counts == {"A": 10, "B": 10, "C": 10}


def test_preference_pilot_merge_cases_need_every_writer_group():
    from src.cases.preference_pilot import pilot_cases

    merge_cases = [
        case for case in pilot_cases()
        if case["primary_capability"] == "cross_agent_merge"
    ]
    assert len(merge_cases) == 4
    for case in merge_cases:
        for group in case["ground_truth"]["evidence_groups"]:
            scores = {
                candidate["id"]: len(set(group).intersection(candidate["attributes"]))
                for candidate in case["decision"]["candidates"]
            }
            winners = [
                candidate_id for candidate_id, score in scores.items()
                if score == max(scores.values())
            ]
            assert winners != [case["ground_truth"]["expected_choice"]]


def test_preference_pilot_user_facing_inputs_are_english_and_nonempty():
    import re
    from src.cases.preference_pilot import pilot_cases

    cjk = re.compile(r"[\u3400-\u9fff]")
    for case in pilot_cases():
        texts = [write["utterance"] for write in case["writes"]]
        texts.extend([
            case["decision"]["task"],
            case["decision"]["memory_query"],
            *[candidate["description"] for candidate in case["decision"]["candidates"]],
        ])
        assert all(text.strip() for text in texts)
        assert not any(cjk.search(text) for text in texts)


def test_preference_pilot_temporary_writes_are_held_constant_in_pairs():
    from collections import defaultdict
    from src.cases.preference_pilot import pilot_cases

    pairs = defaultdict(list)
    for case in pilot_cases():
        if case["pair_id"]:
            pairs[case["pair_id"]].append(case)
    for pair in pairs.values():
        left, right = pair
        assert left["writes"][-1]["preference_kind"] == "temporary"
        assert left["writes"][-1] == right["writes"][-1]
        assert left["decision"] == right["decision"]


def test_preference_no_history_choice_parser():
    from scripts.check_preference_no_history import _parse_choice

    assert _parse_choice('{"choice":"B","reason":"test"}', False) == "B"
    assert _parse_choice('```json\n{"choice":"UNKNOWN","reason":"test"}\n```', True) == "UNKNOWN"


def test_preference_no_history_has_nine_unique_surfaces():
    from scripts.check_preference_no_history import _surface_id
    from src.cases.preference import smoke_cases

    surfaces = {_surface_id(case["decision"]) for case in smoke_cases()}
    assert len(surfaces) == 9


def test_preference_decision_parser():
    from src.runner import _parse_preference_decision

    assert _parse_preference_decision('{"choice":"C","reason":"符合偏好"}') == {
        "choice": "C",
        "reason": "符合偏好",
    }
    assert _parse_preference_decision('```json\n{"choice":"A","reason":"test"}\n```')["choice"] == "A"


def test_preference_summary_scores_counterfactual_pairs():
    from src.runner import _preference_summary
    from src.cases.preference import smoke_cases

    cases = smoke_cases()
    rows = []
    for case in cases:
        rows.append({
            "case_id": case["case_id"],
            "pair_id": case["pair_id"],
            "layer": case["layer"],
            "primary_capability": case["primary_capability"],
            "system": "fake",
            "correct": True,
            "context_chars": 10,
            "total_seconds": 0.1,
            "error": None,
        })

    summary = _preference_summary(cases, rows)["fake"]
    assert summary["decision_accuracy"] == 1.0
    assert summary["counterfactual_pair_success_rate"] == 1.0
    assert summary["mean_context_chars"] == 10


def test_mem0_write_records_native_noop_without_rejecting_case():
    from src.systems.mem0_system import Mem0System

    class FakeMemory:
        def add(self, *args, **kwargs):
            return {"results": []}

    system = object.__new__(Mem0System)
    system._mem = FakeMemory()
    system._user = "test-user"
    system._write_results = []
    try:
        system.write("agent_a", "A durable preference")
        assert system.debug_write_results() == [{
            "agent_id": "agent_a",
            "text": "A durable preference",
            "result": {"results": []},
        }]
    finally:
        system._mem = None
        system._persist_dir = None


def test_mem0_config_isolates_message_history_with_vector_store():
    from src.systems.mem0_system import _build_config

    config = _build_config("/tmp/example-mem0-case")

    assert config["history_db_path"] == "/tmp/example-mem0-case/history.db"
    assert config["vector_store"]["config"]["path"] == "/tmp/example-mem0-case"


def test_deepseek_retry_classification():
    from openai import APIConnectionError, APIStatusError
    from src.agent import _is_retryable

    request = __import__("httpx").Request("POST", "https://api.deepseek.com/v1/chat/completions")
    assert _is_retryable(APIConnectionError(request=request))
    assert _is_retryable(APIStatusError("server error", response=__import__("httpx").Response(503, request=request), body=None))
    assert not _is_retryable(APIStatusError("no credit", response=__import__("httpx").Response(402, request=request), body=None))
