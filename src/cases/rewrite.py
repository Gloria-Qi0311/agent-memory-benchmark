"""Rewrite-preservation task generator.

Each case has three phases:
  1. Initial writes: N facts about a persona.
  2. Update: one fact is explicitly changed (e.g. "X switched from A to B").
  3. Probes: query each fact independently — one should reflect the update,
     the other N-1 should be unchanged from initial.

This isolates two distinct capabilities of a memory system:
  - update_correct: did the updated fact get reflected?
  - preservation_rate: did the system avoid damaging the other N-1 facts?

`naive_markdown` (append-only, no update logic) should hit ~50% on
update_correct (it stores both old and new facts; the reader picks one)
and 100% on preservation_rate. `mem0` (has internal update reconciliation)
should hit close to 100% on update_correct but may drop on preservation
because its update logic can have collateral effects.

The update utterance uses an explicit style:
  "{persona} switched to {new} as their {category}. They don't use {old} anymore."
This is the simplified-laboratory version. Real users phrase updates more
implicitly ("Alex now uses Rust") — that's a v1.5 variant we should test
later, but starting with the explicit version isolates the memory-system
behavior from any ambiguity-resolution layer.
"""
import json
import random
from pathlib import Path
from dataclasses import dataclass, asdict, field

from .fusion import PERSONA_NAMES, FACT_CATEGORIES


@dataclass
class RewriteCase:
    case_id: str
    persona: str

    initial_facts: dict[str, str]       # category -> value (the original truth)
    initial_utterances: list[str]       # how those facts are told to the agent

    update_category: str                # which fact is being updated
    update_old_value: str
    update_new_value: str
    update_utterance: str               # how the update is told to the agent

    # Two probe modes — same case is evaluated under both:
    per_fact_probes: list[dict]         # one question per fact
    aggregate_probe: dict               # one question covering all facts

    # Convenience: the "truth after update" — what the system should reflect.
    truth_after_update: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict: return asdict(self)


def _per_fact_probe(persona: str, category: str, expected: str, kind: str) -> dict:
    return {
        "category": category,
        "question": f"What does {persona} use as their {category}?",
        "expected": expected,
        "kind": kind,  # "updated" or "preserved"
    }


def make_case(seed: int, num_facts: int = 5) -> RewriteCase:
    if num_facts > len(FACT_CATEGORIES):
        raise ValueError(f"num_facts={num_facts} exceeds available categories ({len(FACT_CATEGORIES)})")
    if num_facts < 2:
        raise ValueError("num_facts must be >= 2 (need at least one preserved fact alongside the updated one)")

    r = random.Random(seed)
    persona = r.choice(PERSONA_NAMES)
    cats = r.sample(list(FACT_CATEGORIES.keys()), k=num_facts)
    initial_facts = {c: r.choice(FACT_CATEGORIES[c]) for c in cats}
    initial_utterances = [
        f"{persona} uses {v} as their {c}." for c, v in initial_facts.items()
    ]

    # Pick one category to update; pick a new value distinct from the old.
    update_category = r.choice(cats)
    update_old_value = initial_facts[update_category]
    pool = [v for v in FACT_CATEGORIES[update_category] if v != update_old_value]
    update_new_value = r.choice(pool)
    update_utterance = (
        f"{persona} switched to {update_new_value} as their {update_category}. "
        f"They don't use {update_old_value} anymore."
    )

    truth_after_update = dict(initial_facts)
    truth_after_update[update_category] = update_new_value

    per_fact_probes = [
        _per_fact_probe(
            persona, c, truth_after_update[c],
            kind=("updated" if c == update_category else "preserved"),
        )
        for c in cats
    ]
    aggregate_probe = {
        "question": (
            f"What does {persona} use for {', '.join(cats)}? "
            f"List one item per category."
        ),
        "expected_facts": list(truth_after_update.values()),
        "expected_by_category": dict(truth_after_update),
    }

    return RewriteCase(
        case_id=f"rewrite-{seed:04d}",
        persona=persona,
        initial_facts=initial_facts,
        initial_utterances=initial_utterances,
        update_category=update_category,
        update_old_value=update_old_value,
        update_new_value=update_new_value,
        update_utterance=update_utterance,
        per_fact_probes=per_fact_probes,
        aggregate_probe=aggregate_probe,
        truth_after_update=truth_after_update,
    )


def generate(n: int, out_path: Path, seed: int = 0, num_facts: int = 5) -> None:
    cases = [make_case(seed + i, num_facts=num_facts) for i in range(n)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([c.to_dict() for c in cases], indent=2))
