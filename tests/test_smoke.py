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
