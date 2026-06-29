"""Smoke test — does the case generator and judge work without an API key?
Run: pytest tests/
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.cases import fusion
from src.judge import fusion_score
from src.systems.no_memory import NoMemory
from src.systems.naive_markdown import NaiveMarkdown
from src.systems.long_context import LongContext
from src.systems.regex_markdown import RegexMarkdown, _extract_retired_values


def test_case_generator_deterministic():
    a = fusion.make_case(seed=42)
    b = fusion.make_case(seed=42)
    assert a.case_id == b.case_id
    assert a.ground_truth_facts == b.ground_truth_facts
    assert len(a.ground_truth_facts) == 4


def test_judge_perfect_recall():
    case = fusion.make_case(seed=1)
    answer = " ".join(case.ground_truth_facts)
    s = fusion_score(answer, case.ground_truth_facts)
    assert s["recall"] == 1.0


def test_judge_zero_recall():
    s = fusion_score("nothing here", ["Python", "React"])
    assert s["recall"] == 0.0


def test_naive_markdown_roundtrip():
    m = NaiveMarkdown()
    m.write("agent_a", "Alex uses Python")
    m.write("agent_b", "Alex lives in Berlin")
    ctx = m.read("agent_c", "tell me about alex")
    assert "Python" in ctx and "Berlin" in ctx


def test_no_memory_is_empty():
    m = NoMemory()
    m.write("agent_a", "something")
    assert m.read("agent_c", "?") == ""


def test_long_context_strips_agent_tag():
    m = LongContext()
    m.write("agent_a", "Alex uses Python.")
    m.write("agent_b", "Alex switched to Rust.")
    ctx = m.read("agent_c", "?")
    assert "Alex uses Python." in ctx
    assert "Alex switched to Rust." in ctx
    assert "agent_a" not in ctx
    assert "agent_b" not in ctx


def test_regex_retire_extraction():
    assert _extract_retired_values("They don't use Python anymore.") == ["Python"]
    assert _extract_retired_values("They no longer use AWS.") == ["AWS"]
    assert _extract_retired_values("Alex switched to Rust. They don't use Python anymore.") == ["Python"]
    assert _extract_retired_values("Alex uses Python.") == []


def test_regex_markdown_drops_retired_fact():
    m = RegexMarkdown()
    m.write("agent_a", "Alex uses Python as their language.")
    m.write("agent_a", "Alex uses VSCode as their editor.")
    m.write("agent_b", "Alex switched to Rust as their language. They don't use Python anymore.")
    ctx = m.read("agent_c", "?")
    # The old "Alex uses Python" entry should be GONE.
    assert "uses Python as" not in ctx
    # The new statement should still be there.
    assert "Rust" in ctx
    # The unrelated fact should still be there.
    assert "VSCode" in ctx


def test_regex_markdown_preserves_unrelated_facts():
    m = RegexMarkdown()
    m.write("agent_a", "Alex uses Python as their language.")
    m.write("agent_a", "Alex uses VSCode as their editor.")
    m.write("agent_a", "Alex uses pytest as their test.")
    m.write("agent_b", "Alex switched to Rust as their language. They don't use Python anymore.")
    ctx = m.read("agent_c", "?")
    assert "VSCode" in ctx
    assert "pytest" in ctx
