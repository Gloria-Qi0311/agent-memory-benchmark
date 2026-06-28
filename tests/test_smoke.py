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
