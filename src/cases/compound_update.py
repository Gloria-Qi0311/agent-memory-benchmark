"""T2 — Compound update task generator.

Each case has three phases:
  Phase 1 — Initial state: N atomic facts about a persona, written one
            per call to the memory system (agent_a is the "writer").
  Phase 2 — Compound update: agent_b tells the memory system that K of
            those N facts changed, all in a single statement, using
            EXPLICIT phrasing ("moved from X to Y") — this is fair to
            mem0, which needs an explicit signal to trigger its
            update-reconciliation logic.
  Phase 3 — Read (probes): agent_c, which has never written anything,
            asks about each of the N facts. Probes cover:
              - K "updated" probes: the truth is the new value
              - (N-K) "preserved" probes: the truth is the initial value

This is the first task in the benchmark where three distinct agent
identities span three distinct time steps. T4 was single-write /
single-read; T2 is initial-writes / update-write / delayed-read.

Metrics evaluated (see runner + judge):
  update_recall: fraction of the K updated probes hit
  no_confusion: for the K updated probes, is the new value assigned to
                the RIGHT category (not swapped with another updated one)
  no_collateral: fraction of the (N-K) preserved probes hit

Reuses T4's SCENARIOS pool for values (same personas, same categories,
same value distributions) so T2 findings are directly comparable to T4
findings on the same substrate.
"""
import json
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .split_intake import SCENARIOS, PERSONA_NAMES, _LAPTOP_OS_COMPAT, _TRAVEL_DATE_PAIRS


_INITIAL_UTTERANCE_TEMPLATES = {
    "dev_setup": {
        "laptop":      "{persona}'s laptop is a {value}.",
        "ram":         "{persona}'s machine has {value} of RAM.",
        "storage":     "{persona} has {value} of storage.",
        "display":     "{persona}'s display is a {value}.",
        "keyboard":    "{persona}'s keyboard is a {value}.",
        "os":          "{persona} runs {value}.",
        "shell":       "{persona} uses {value} as their shell.",
        "ide":         "{persona} uses {value} as their primary IDE.",
        "terminal":    "{persona}'s terminal is {value}.",
        "font":        "{persona}'s coding font is {value}.",
        "theme":       "{persona}'s editor theme is {value}.",
        "package_mgr": "{persona} manages packages with {value}.",
        "git_client":  "{persona}'s git client is {value}.",
    },
    "travel_plan": {
        "destination":      "{persona} is traveling to {value}.",
        "departure_city":   "{persona} is departing from {value}.",
        "depart_date":      "{persona} departs on {value}.",
        "return_date":      "{persona} returns on {value}.",
        "airline":          "{persona} is flying {value}.",
        "flight_class":     "{persona} is in {value} class.",
        "seat_pref":        "{persona} has a {value} seat.",
        "hotel":            "{persona} is staying at the {value}.",
        "hotel_room":       "{persona} is in a {value} room.",
        "purpose":          "{persona}'s trip is a {value}.",
        "meal_pref":        "{persona} requested a {value} meal.",
        "travel_companion": "{persona} is traveling {value}.",
    },
    "home_office": {
        "desk":            "{persona}'s desk is a {value}.",
        "chair":           "{persona}'s chair is a {value}.",
        "monitor_mount":   "{persona}'s monitor mount is a {value}.",
        "lighting":        "{persona}'s call lighting is {value}.",
        "webcam":          "{persona}'s webcam is a {value}.",
        "mic":             "{persona}'s microphone is a {value}.",
        "speakers":        "{persona}'s speakers are {value}.",
        "audio_interface": "{persona}'s audio interface is a {value}.",
        "headphones":      "{persona}'s headphones are {value}.",
        "notebook":        "{persona}'s notebook is a {value}.",
        "plant":           "{persona}'s office plant is a {value}.",
        "background":      "{persona}'s call background is a {value}.",
    },
}

# Human-readable labels for each key (used in the update statement and probes).
_LABEL = {
    # dev_setup
    "laptop": "laptop", "ram": "RAM", "storage": "storage",
    "display": "display", "keyboard": "keyboard", "os": "operating system",
    "shell": "shell", "ide": "IDE", "terminal": "terminal",
    "font": "coding font", "theme": "editor theme",
    "package_mgr": "package manager", "git_client": "git client",
    # travel_plan
    "destination": "destination", "departure_city": "departure city",
    "depart_date": "departure date", "return_date": "return date",
    "airline": "airline", "flight_class": "flight class",
    "seat_pref": "seat preference", "hotel": "hotel",
    "hotel_room": "hotel room type", "purpose": "trip purpose",
    "meal_pref": "meal preference", "travel_companion": "travel companion",
    # home_office
    "desk": "desk", "chair": "chair", "monitor_mount": "monitor mount",
    "lighting": "lighting", "webcam": "webcam", "mic": "microphone",
    "speakers": "speakers", "audio_interface": "audio interface",
    "headphones": "headphones", "notebook": "notebook",
    "plant": "office plant", "background": "call background",
}


_PROBE_TEMPLATES = {
    # dev_setup
    "laptop":      "What laptop does {persona} use?",
    "ram":         "How much RAM does {persona}'s machine have?",
    "storage":     "How much storage does {persona}'s machine have?",
    "display":     "What display does {persona} use?",
    "keyboard":    "What keyboard does {persona} use?",
    "os":          "What operating system does {persona} run?",
    "shell":       "What shell does {persona} use?",
    "ide":         "What IDE does {persona} use?",
    "terminal":    "What terminal does {persona} use?",
    "font":        "What coding font does {persona} use?",
    "theme":       "What editor theme does {persona} use?",
    "package_mgr": "What package manager does {persona} use?",
    "git_client":  "What git client does {persona} use?",
    # travel_plan
    "destination":      "Where is {persona} traveling to?",
    "departure_city":   "Where is {persona} departing from?",
    "depart_date":      "When does {persona} depart?",
    "return_date":      "When does {persona} return?",
    "airline":          "What airline is {persona} flying?",
    "flight_class":     "What flight class is {persona} in?",
    "seat_pref":        "What seat preference does {persona} have?",
    "hotel":            "Where is {persona} staying?",
    "hotel_room":       "What room type is {persona} booked in?",
    "purpose":          "What's the purpose of {persona}'s trip?",
    "meal_pref":        "What meal preference did {persona} request?",
    "travel_companion": "Who is {persona} traveling with?",
    # home_office
    "desk":            "What desk does {persona} have?",
    "chair":           "What chair does {persona} use?",
    "monitor_mount":   "What monitor mount does {persona} have?",
    "lighting":        "What lighting does {persona} use?",
    "webcam":          "What webcam does {persona} use?",
    "mic":             "What microphone does {persona} use?",
    "speakers":        "What speakers does {persona} use?",
    "audio_interface": "What audio interface does {persona} have?",
    "headphones":      "What headphones does {persona} use?",
    "notebook":        "What notebook does {persona} carry?",
    "plant":           "What plant does {persona} have in the office?",
    "background":      "What's the background behind {persona} on calls?",
}


@dataclass
class CompoundUpdateCase:
    case_id: str
    scenario: str
    persona: str
    initial_facts: dict         # key -> initial value (before update)
    updated_facts: dict         # key -> new value (only the K updated keys)
    initial_utterances: list    # what agent_a writes, one string per fact
    update_utterance: str       # the single statement agent_b writes
    probes: list                # list of {"key","kind","expected","question"}

    def to_dict(self) -> dict: return asdict(self)


def _pick_initial_facts(r: random.Random, scenario_name: str, scenario: dict,
                         n: int) -> dict:
    """Pick N initial facts with the same constraints T4 uses (laptop-OS
    compat for dev_setup, chronologically-sane date pairs for travel_plan).
    T2's N (10) is smaller than T4's max (12-13) so subsampling is fine."""
    keys = scenario["keys"]
    if n > len(keys):
        raise ValueError(f"scenario {scenario_name} only has {len(keys)} keys, need {n}")

    if scenario_name == "dev_setup":
        sampled = r.sample(keys, k=n)
        vals = {k: r.choice(scenario["values"][k]) for k in sampled}
        # Enforce laptop-OS compatibility if both were sampled.
        if "laptop" in vals and "os" in vals:
            vals["os"] = r.choice(_LAPTOP_OS_COMPAT[vals["laptop"]])
        return vals

    if scenario_name == "travel_plan":
        sampled = r.sample(keys, k=n)
        vals = {}
        # Pick a chronologically-sane date pair if either date key was sampled.
        depart, ret = r.choice(_TRAVEL_DATE_PAIRS)
        for k in sampled:
            if k == "depart_date":
                vals[k] = depart
            elif k == "return_date":
                vals[k] = ret
            else:
                vals[k] = r.choice(scenario["values"][k])
        return vals

    # home_office: independent samples.
    sampled = r.sample(keys, k=n)
    return {k: r.choice(scenario["values"][k]) for k in sampled}


def _pick_update_targets(r: random.Random, initial_facts: dict, scenario: dict,
                        k: int) -> dict:
    """Pick K keys to update; new value must differ from initial and be from
    the same category pool.

    Constraints preserved:
      - dev_setup: if laptop is being updated, os must be compatible.
      - travel_plan: depart_date and return_date must remain a valid pair.
        If either is being updated, pick a fresh pair from _TRAVEL_DATE_PAIRS
        that differs from the initial pair.
    """
    keys = list(initial_facts.keys())
    updated_keys = r.sample(keys, k=k)

    new_vals: dict[str, str] = {}
    for key in updated_keys:
        # date keys handled below in the travel-date block
        if key in ("depart_date", "return_date"):
            new_vals[key] = None  # placeholder, fixed up below
            continue
        pool = [v for v in scenario["values"][key] if v != initial_facts[key]]
        new_vals[key] = r.choice(pool)

    # travel_plan: any date key being updated triggers a fresh pair.
    if "depart_date" in new_vals or "return_date" in new_vals:
        # Every field labeled as updated must actually change. Comparing only
        # the full pair is insufficient when the case sampled just one date.
        candidate_pairs = [
            pair for pair in _TRAVEL_DATE_PAIRS
            if ("depart_date" not in new_vals
                or pair[0] != initial_facts["depart_date"])
            and ("return_date" not in new_vals
                 or pair[1] != initial_facts["return_date"])
        ]
        if not candidate_pairs:
            raise ValueError("no date pair available for a real update")
        depart, ret = r.choice(candidate_pairs)
        if "depart_date" in new_vals:
            new_vals["depart_date"] = depart
        if "return_date" in new_vals:
            new_vals["return_date"] = ret

    # dev_setup: if laptop is updated, keep os compatible.
    if "laptop" in new_vals:
        compatible_os = _LAPTOP_OS_COMPAT[new_vals["laptop"]]
        if "os" in new_vals:
            # A compatibility fix must not turn an authored update into the
            # nonsensical "from X to X". Prefer any compatible OS other than
            # the initial value; all current laptop pools provide one.
            choices = [os_name for os_name in compatible_os
                       if os_name != initial_facts["os"]]
            if not choices:
                raise ValueError("no compatible OS available for a real update")
            new_vals["os"] = r.choice(choices)
        # If os is NOT being updated but initial os is incompatible with new
        # laptop, we leave it — the case is contrived but not broken (user
        # switched laptops but hasn't switched OSes yet). Acceptable for v1.

    return new_vals


def _build_update_utterance(persona: str, updates: dict, initial: dict) -> str:
    """Construct an explicit multi-clause update statement.

    Example (K=4):
      "{persona} moved their language from Python to TypeScript, their
       framework from Django to Next.js, their cloud from AWS to
       Cloudflare, and their CI from GitHub Actions to Vercel."
    """
    parts = []
    for key, new_val in updates.items():
        old_val = initial[key]
        label = _LABEL[key]
        parts.append(f"their {label} from {old_val} to {new_val}")

    if len(parts) == 1:
        body = parts[0]
    elif len(parts) == 2:
        body = " and ".join(parts)
    else:
        body = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    return f"{persona} switched {body}."


def make_case(seed: int, scenario_name: str | None = None,
              n: int = 10, k: int = 4) -> CompoundUpdateCase:
    if k >= n:
        raise ValueError(f"k ({k}) must be < n ({n})")

    r = random.Random(seed)
    scenario_name = scenario_name or r.choice(list(SCENARIOS.keys()))
    scenario = SCENARIOS[scenario_name]
    persona = r.choice(PERSONA_NAMES)

    initial_facts = _pick_initial_facts(r, scenario_name, scenario, n)
    updated_facts = _pick_update_targets(r, initial_facts, scenario, k)

    # Initial utterances: one per fact, spelled out plainly.
    templates = _INITIAL_UTTERANCE_TEMPLATES[scenario_name]
    initial_utterances = [
        templates[key].format(persona=persona, value=val)
        for key, val in initial_facts.items()
    ]

    # Update statement: single explicit multi-clause sentence.
    update_utterance = _build_update_utterance(persona, updated_facts, initial_facts)

    # Probes: for each of the N keys, ask the question. Expected value is
    # the updated value if that key was updated, else the initial value.
    probes = []
    for key in initial_facts:
        if key in updated_facts:
            expected = updated_facts[key]
            kind = "updated"
        else:
            expected = initial_facts[key]
            kind = "preserved"
        probes.append({
            "key": key,
            "kind": kind,
            "expected": expected,
            "question": _PROBE_TEMPLATES[key].format(persona=persona),
        })

    return CompoundUpdateCase(
        case_id=f"T2-{seed:04d}",
        scenario=scenario_name,
        persona=persona,
        initial_facts=initial_facts,
        updated_facts=updated_facts,
        initial_utterances=initial_utterances,
        update_utterance=update_utterance,
        probes=probes,
    )


def validate_case(case: dict) -> None:
    """Validate T2 ground truth without calling an LLM.

    This checks the authored state transition: updated keys change to the
    probe's new value, preserved keys retain the initial value, and every
    explicit old/new value is present in the compound update utterance.
    """
    initial = case["initial_facts"]
    updated = case["updated_facts"]
    probes = case["probes"]
    update_text = case["update_utterance"]

    if not updated or not set(updated).issubset(initial):
        raise ValueError(f"{case['case_id']}: updated keys must be a nonempty subset")
    if len(probes) != len(initial):
        raise ValueError(f"{case['case_id']}: expected one probe per initial fact")
    if len({p["key"] for p in probes}) != len(probes):
        raise ValueError(f"{case['case_id']}: duplicate probe keys")

    for key, new_value in updated.items():
        old_value = initial[key]
        if new_value == old_value:
            raise ValueError(f"{case['case_id']}: {key} does not actually change")
        if old_value not in update_text or new_value not in update_text:
            raise ValueError(f"{case['case_id']}: update text omits {key}'s old/new value")

    by_key = {probe["key"]: probe for probe in probes}
    if set(by_key) != set(initial):
        raise ValueError(f"{case['case_id']}: probe keys do not equal fact keys")
    for key, old_value in initial.items():
        probe = by_key[key]
        expected_kind = "updated" if key in updated else "preserved"
        expected_value = updated.get(key, old_value)
        if probe["kind"] != expected_kind or probe["expected"] != expected_value:
            raise ValueError(f"{case['case_id']}: inconsistent ground truth for {key}")


def generate(n: int, out_path: Path, seed: int = 0,
             n_facts: int = 10, k_updates: int = 4) -> None:
    cases = [make_case(seed + i, n=n_facts, k=k_updates) for i in range(n)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([c.to_dict() for c in cases], indent=2, ensure_ascii=False))
