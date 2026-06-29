"""Smoke tests — sanity-check the system adapters without hitting any LLM API.
Run: pytest tests/

T4 (split intake) judge/runner tests are added in Phase A of T4 work.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.judge import _match
from src.systems.no_memory import NoMemory
from src.systems.naive_markdown import NaiveMarkdown
from src.systems.long_context import LongContext


def test_match_word_boundary():
    # _match's contract: caller passes ALREADY-LOWERCASED text.
    # word-boundary so "Go" doesn't match "Going"
    assert _match("Go", "i'm using go on aws")
    assert not _match("Go", "i'm going to aws")
    # case-insensitive on the value (matched against lowercased text)
    assert _match("Python", "alex uses python")
    # punctuation around the token is fine
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
