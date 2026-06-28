"""Fusion task generator.

Each case:
  - persona with N facts (split between agent A and agent B)
  - a probe question that requires using BOTH halves
  - ground-truth fact list for programmatic scoring
"""
import json
import random
from pathlib import Path
from dataclasses import dataclass, asdict


PERSONA_NAMES = ["Alex", "Bao", "Chloe", "Diego", "Eun", "Farida", "Gabriel", "Hana"]

# Fact values are chosen to be distinctive English tokens (avoiding bare
# "Go" / "Render" which collide with common verbs and trip up substring
# matching). The judge already uses word boundaries, but distinctive
# names make hits and misses unambiguous when reading raw answers.
FACT_CATEGORIES = {
    "language": ["Python", "TypeScript", "Golang", "Rust", "Swift"],
    "framework": ["React", "Django", "FastAPI", "SvelteKit", "Rails"],
    "editor": ["VSCode", "Cursor", "Neovim", "Zed", "JetBrains"],
    "cloud": ["AWS", "GCP", "Cloudflare", "Fly.io", "Render.com"],
    "db": ["Postgres", "MongoDB", "DynamoDB", "SQLite", "Supabase"],
    "ci": ["GitHub Actions", "CircleCI", "Buildkite", "Drone CI", "GitLab CI"],
    "test": ["pytest", "vitest", "jest", "playwright", "cypress"],
    "city": ["Berlin", "Lisbon", "Taipei", "Toronto", "Bangalore"],
}


@dataclass
class FusionCase:
    case_id: str
    persona: str
    facts_a: dict       # category -> value, written by agent A
    facts_b: dict       # category -> value, written by agent B
    a_utterances: list  # what A "tells" the memory system
    b_utterances: list
    probe_question: str
    ground_truth_facts: list  # values that must appear in C's answer

    def to_dict(self) -> dict: return asdict(self)


def make_case(seed: int) -> FusionCase:
    r = random.Random(seed)
    persona = r.choice(PERSONA_NAMES)
    cats = r.sample(list(FACT_CATEGORIES.keys()), k=4)
    cats_a, cats_b = cats[:2], cats[2:]
    facts_a = {c: r.choice(FACT_CATEGORIES[c]) for c in cats_a}
    facts_b = {c: r.choice(FACT_CATEGORIES[c]) for c in cats_b}

    a_utterances = [f"{persona} uses {v} as their {c}." for c, v in facts_a.items()]
    b_utterances = [f"{persona} uses {v} as their {c}." for c, v in facts_b.items()]

    all_cats = cats_a + cats_b
    probe_question = (
        f"What does {persona} use for {', '.join(all_cats)}? "
        f"List one item per category."
    )
    gt = list(facts_a.values()) + list(facts_b.values())

    return FusionCase(
        case_id=f"fusion-{seed:04d}",
        persona=persona, facts_a=facts_a, facts_b=facts_b,
        a_utterances=a_utterances, b_utterances=b_utterances,
        probe_question=probe_question, ground_truth_facts=gt,
    )


def generate(n: int, out_path: Path, seed: int = 0) -> None:
    cases = [make_case(seed + i) for i in range(n)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([c.to_dict() for c in cases], indent=2))
