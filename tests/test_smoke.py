"""Smoke tests — sanity-check primitives without hitting any LLM API.
Run: pytest tests/
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.judge import _match, split_intake_score_per_detail, split_intake_score_aggregate
from src.systems.no_memory import NoMemory
from src.systems.naive_markdown import NaiveMarkdown
from src.systems.long_context import LongContext


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


def test_long_context_strips_agent_tag():
    m = LongContext()
    m.write("agent_a", "Alex uses Python.")
    m.write("agent_b", "Alex switched to Rust.")
    ctx = m.read("agent_c", "?")
    assert "Alex uses Python." in ctx
    assert "Alex switched to Rust." in ctx
    assert "agent_a" not in ctx
    assert "agent_b" not in ctx


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
