"""T4 — Split intake task generator.

A case is a single dense user statement containing N atomic details
that should each be independently recallable. The memory system is
expected to handle decomposition internally — we do NOT pre-split.

Case construction (hybrid programmatic + LLM rephrase):
  1. Programmatically pick ground-truth details (key -> value) from
     a scenario-specific pool, with realism constraints (laptop-OS
     compatibility, chronologically-sane travel dates).
  2. Build a skeleton sentence from the scenario template that mentions
     every detail verbatim.
  3. Optionally inject 0-2 noise sentences (unrelated chatter) before
     and/or after the signal.
  4. Ask the LLM to rephrase the result into a natural-sounding user
     statement, keeping every value verbatim. Retry up to 3 times.
  5. Verify by word-boundary match that every ground-truth value still
     appears in the rephrased statement. If still missing after retries,
     fall back to the (un-rephrased) skeleton + noise.

Each scenario carries 12-13 detail keys so a single case packs enough
information density to exercise extraction. Noise injection (~50% of
cases) tests whether systems can isolate signal from chatter.

Probes come in two modes per case:
  - per_detail: one targeted question per key
  - aggregate: one broad question listing all keys
"""
import json
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from ..agent import chat


PERSONA_NAMES = ["Alex", "Bao", "Chloe", "Diego", "Eun", "Farida", "Gabriel", "Hana"]


SCENARIOS = {
    "dev_setup": {
        "keys": [
            "laptop", "ram", "storage", "display", "keyboard", "os",
            "shell", "ide", "terminal", "font", "theme", "package_mgr", "git_client",
        ],
        # `os` is sampled after `laptop` and constrained by _LAPTOP_OS_COMPAT.
        "values": {
            "laptop":      ["MacBook Pro M4 Max", "MacBook Air M3", "ThinkPad X1 Carbon Gen 12", "Framework 13", "Surface Laptop 6"],
            "ram":         ["32GB", "48GB", "64GB", "96GB", "128GB"],
            "storage":     ["1TB SSD", "2TB SSD", "4TB SSD", "8TB SSD"],
            "display":     ["Studio Display 5K", "Pro Display XDR", "ASUS ProArt PA32UCG", "LG UltraFine 5K", "Dell U4025QW"],
            "keyboard":    ["Keychron Q3 Pro", "HHKB Studio", "ZSA Voyager", "Glove80", "Moonlander Mark I"],
            "os":          ["macOS Sequoia", "macOS Sonoma", "Ubuntu 24.04", "Arch Linux", "Fedora 41"],
            "shell":       ["zsh", "fish", "nushell", "bash"],
            "ide":         ["Cursor", "VSCode", "Zed", "Neovim", "JetBrains Rider"],
            "terminal":    ["Ghostty", "WezTerm", "iTerm2", "Kitty", "Alacritty"],
            "font":        ["JetBrains Mono", "Berkeley Mono", "Fira Code", "Cascadia Code", "Monaspace Argon"],
            "theme":       ["Catppuccin Mocha", "Tokyo Night", "One Dark", "Solarized Dark", "Rose Pine"],
            "package_mgr": ["Homebrew", "Nix", "pacman", "apt", "dnf"],
            "git_client":  ["GitHub Desktop", "GitKraken", "Tower", "Fork", "lazygit"],
        },
        "probes": {
            "laptop":      "What laptop does {persona} use?",
            "ram":         "How much RAM does {persona}'s machine have?",
            "storage":     "What storage does {persona}'s machine have?",
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
        },
        "skeleton": (
            "{persona} just rebuilt their dev setup. The hardware: {laptop} with "
            "{ram} RAM and {storage}, paired with a {display} and a {keyboard}. "
            "Software side, they run {os} with {shell} as their shell, {ide} as the "
            "primary IDE, and {terminal} as the terminal. The look: {font} as the "
            "coding font, {theme} as the theme. For tooling, they manage packages "
            "with {package_mgr} and use {git_client} as their git client."
        ),
    },

    "travel_plan": {
        "keys": [
            "destination", "departure_city", "depart_date", "return_date",
            "airline", "flight_class", "seat_pref", "hotel", "hotel_room",
            "purpose", "meal_pref", "travel_companion",
        ],
        # depart_date and return_date are picked as a chronologically-sane pair
        # by _pick_values.
        "values": {
            "destination":      ["Tokyo", "Lisbon", "Reykjavik", "Buenos Aires", "Cape Town", "Bali", "Marrakech"],
            "departure_city":   ["Seattle", "London", "Toronto", "Singapore", "Berlin", "Dubai"],
            "depart_date":      [],  # see _TRAVEL_DATE_PAIRS
            "return_date":      [],
            "airline":          ["ANA", "Lufthansa", "Singapore Airlines", "Qatar Airways", "Emirates", "Air France"],
            "flight_class":     ["Economy", "Premium Economy", "Business", "First"],
            "seat_pref":        ["window", "aisle", "bulkhead"],
            "hotel":            ["Park Hyatt", "Aman", "Ritz-Carlton", "Mandarin Oriental", "Rosewood", "Soho House"],
            "hotel_room":       ["King Deluxe", "Suite", "Twin", "Studio"],
            "purpose":          ["conference talk", "vacation", "client meeting", "wedding", "research trip", "honeymoon"],
            "meal_pref":        ["vegetarian", "kosher", "gluten-free", "no special meal"],
            "travel_companion": ["solo", "with their partner", "with family"],
        },
        "probes": {
            "destination":      "Where is {persona} traveling to?",
            "departure_city":   "Where is {persona} departing from?",
            "depart_date":      "When does {persona} depart?",
            "return_date":      "When does {persona} return?",
            "airline":          "What airline is {persona} flying?",
            "flight_class":     "What flight class is {persona} in?",
            "seat_pref":        "What seat preference does {persona} have?",
            "hotel":             "Where is {persona} staying?",
            "hotel_room":       "What room type is {persona} booked in?",
            "purpose":          "What's the purpose of {persona}'s trip?",
            "meal_pref":        "What meal preference did {persona} request?",
            "travel_companion": "Who is {persona} traveling with?",
        },
        "skeleton": (
            "{persona} is taking a trip — {departure_city} to {destination}, "
            "{depart_date} through {return_date}, traveling {travel_companion}. "
            "It's a {purpose}. They're flying {airline} in {flight_class} with a "
            "{seat_pref} seat, having requested a {meal_pref} meal. Staying at the "
            "{hotel} in a {hotel_room}."
        ),
    },

    "home_office": {
        "keys": [
            "desk", "chair", "monitor_mount", "lighting", "webcam", "mic", "speakers",
            "audio_interface", "headphones", "notebook", "plant", "background",
        ],
        "values": {
            "desk":            ["Uplift V2", "Jarvis Standing Desk", "Fully Cooper", "FlexiSpot E7", "IKEA Bekant"],
            "chair":           ["Herman Miller Aeron", "Steelcase Leap V2", "Embody", "Secretlab Titan", "Branch Ergonomic"],
            "monitor_mount":   ["Ergotron LX", "Jarvis Single Arm", "Humanscale M2.1", "Fully Jarvis", "IKEA Tertial"],
            "lighting":        ["Elgato Key Light", "BenQ ScreenBar Halo", "Philips Hue Play", "Govee Glide", "Logitech Litra Glow"],
            "webcam":          ["Logitech Brio 4K", "Insta360 Link", "Opal Tadpole", "Sony ZV-1F", "Elgato Facecam"],
            "mic":             ["Shure SM7B", "Rode PodMic", "Blue Yeti X", "Audio-Technica AT2020", "Elgato Wave 3"],
            "speakers":        ["Audioengine A2+", "KEF LSX II", "Edifier R1700BT", "Genelec 8010A", "Yamaha HS5"],
            "audio_interface": ["Focusrite Scarlett 2i2", "RME Babyface Pro", "Apollo Twin X", "MOTU M2", "SSL 2+"],
            "headphones":      ["Sony WH-1000XM5", "AirPods Max", "Sennheiser HD 660S2", "Bose QC Ultra", "Audeze LCD-X"],
            "notebook":        ["Moleskine", "Leuchtturm1917", "Hobonichi Techo", "Field Notes", "Midori MD"],
            "plant":           ["Monstera", "Pothos", "Snake Plant", "Fiddle Leaf Fig", "ZZ Plant"],
            "background":      ["bookshelf", "brick wall", "acoustic panel", "virtual"],
        },
        "probes": {
            "desk":             "What desk does {persona} have?",
            "chair":            "What chair does {persona} use?",
            "monitor_mount":    "What monitor mount does {persona} have?",
            "lighting":         "What lighting does {persona} use?",
            "webcam":           "What webcam does {persona} use?",
            "mic":              "What microphone does {persona} use?",
            "speakers":         "What speakers does {persona} use?",
            "audio_interface":  "What audio interface does {persona} have?",
            "headphones":       "What headphones does {persona} use?",
            "notebook":         "What notebook does {persona} carry?",
            "plant":            "What plant does {persona} have in the office?",
            "background":       "What's the background behind {persona} on calls?",
        },
        "skeleton": (
            "{persona} finally finished their home office. The desk is a {desk}, "
            "the chair is a {chair}, monitor on a {monitor_mount}. For calls: "
            "{lighting} lighting, {webcam} webcam, {mic} microphone, {speakers} "
            "speakers, {audio_interface} as the audio interface. Personal touches: "
            "{headphones} for headphones, a {notebook} notebook on the desk, a "
            "{plant} in the corner, and a {background} background."
        ),
    },
}


# Chronologically-sane (depart, return) date pairs — same month or adjacent month.
_TRAVEL_DATE_PAIRS = [
    ("March 14", "March 28"),
    ("April 22", "May 6"),
    ("May 8", "May 20"),
    ("September 3", "September 17"),
    ("November 19", "December 3"),
    ("December 1", "December 15"),
]

# laptop -> compatible operating systems. Apple Silicon doesn't run mainstream
# Linux distros well; macOS doesn't run on non-Apple hardware.
_LAPTOP_OS_COMPAT = {
    "MacBook Pro M4 Max":        ["macOS Sequoia", "macOS Sonoma"],
    "MacBook Air M3":            ["macOS Sequoia", "macOS Sonoma"],
    "ThinkPad X1 Carbon Gen 12": ["Ubuntu 24.04", "Arch Linux", "Fedora 41"],
    "Framework 13":              ["Ubuntu 24.04", "Arch Linux", "Fedora 41"],
    "Surface Laptop 6":          ["Ubuntu 24.04", "Arch Linux", "Fedora 41"],
}

# Unrelated chatter sentences sprinkled into the user statement. They are written
# in neutral third-person voice so they don't fight the third-person skeleton.
# They must not mention any value or category in SCENARIOS — otherwise they'd
# interfere with ground-truth probes.
_NOISE_SENTENCES = [
    "By the way, the espresso this morning was great.",
    "Anyway — that's the update.",
    "There's a new book on systems design sitting on the desk.",
    "The cat just knocked over a glass of water.",
    "It's been raining nonstop this week.",
    "Lunch got skipped again today.",
    "Spotify keeps recommending the same album lately.",
    "The coffee beans need refilling tomorrow.",
    "The kettle is still warm.",
    "An old podcast episode is playing in the background.",
]


REPHRASE_SYSTEM = """You're given a stilted but factually correct statement, written in third person, about a person's setup or plan. Rewrite it in a more natural, flowing style. Keep it to 3-6 sentences.

STRICT REQUIREMENTS:
- Keep the third-person voice. Continue referring to the person by their name (as in the input). Do NOT switch to first person ("I", "my").
- Keep EVERY product name, brand, model, place name, date, and number EXACTLY as given. Do not paraphrase them, do not abbreviate them, do not translate them.
- Do not add facts that weren't in the original.
- Do not remove any of the original facts.
- Output ONLY the rewritten statement. No preamble, no quotes."""


def _match(value: str, text: str) -> bool:
    """Word-boundary, case-insensitive substring match."""
    return re.search(r"\b" + re.escape(value.lower()) + r"\b", text.lower()) is not None


@dataclass
class SplitIntakeCase:
    case_id: str
    scenario: str
    persona: str
    ground_truth_details: dict        # key -> value (canonical truth)
    skeleton_statement: str           # programmatic skeleton WITHOUT noise (always faithful)
    skeleton_with_noise: str          # skeleton + injected noise sentences
    user_statement: str               # natural-voice version actually fed to memory
    noise_sentences: list             # noise lines used (for transparency)
    used_fallback: bool               # True if LLM rephrase never preserved all values
    n_rephrase_attempts: int          # how many LLM calls were made
    per_detail_probes: list
    aggregate_probe: dict

    def to_dict(self) -> dict: return asdict(self)


def _pick_values(r: random.Random, scenario_name: str, scenario: dict) -> dict:
    """Sample one value per key, with scenario-specific constraints:
      - travel_plan: depart/return picked as a chronologically-sane pair.
      - dev_setup:   `os` constrained to be compatible with the chosen `laptop`.
    """
    if scenario_name == "travel_plan":
        depart, ret = r.choice(_TRAVEL_DATE_PAIRS)
        return {
            "destination":      r.choice(scenario["values"]["destination"]),
            "departure_city":   r.choice(scenario["values"]["departure_city"]),
            "depart_date":      depart,
            "return_date":      ret,
            "airline":          r.choice(scenario["values"]["airline"]),
            "flight_class":     r.choice(scenario["values"]["flight_class"]),
            "seat_pref":        r.choice(scenario["values"]["seat_pref"]),
            "hotel":            r.choice(scenario["values"]["hotel"]),
            "hotel_room":       r.choice(scenario["values"]["hotel_room"]),
            "purpose":          r.choice(scenario["values"]["purpose"]),
            "meal_pref":        r.choice(scenario["values"]["meal_pref"]),
            "travel_companion": r.choice(scenario["values"]["travel_companion"]),
        }
    if scenario_name == "dev_setup":
        laptop = r.choice(scenario["values"]["laptop"])
        os_choice = r.choice(_LAPTOP_OS_COMPAT[laptop])
        return {
            "laptop":      laptop,
            "ram":         r.choice(scenario["values"]["ram"]),
            "storage":     r.choice(scenario["values"]["storage"]),
            "display":     r.choice(scenario["values"]["display"]),
            "keyboard":    r.choice(scenario["values"]["keyboard"]),
            "os":          os_choice,
            "shell":       r.choice(scenario["values"]["shell"]),
            "ide":         r.choice(scenario["values"]["ide"]),
            "terminal":    r.choice(scenario["values"]["terminal"]),
            "font":        r.choice(scenario["values"]["font"]),
            "theme":       r.choice(scenario["values"]["theme"]),
            "package_mgr": r.choice(scenario["values"]["package_mgr"]),
            "git_client":  r.choice(scenario["values"]["git_client"]),
        }
    # home_office and any future independent-keys scenarios
    return {k: r.choice(scenario["values"][k]) for k in scenario["keys"]}


def _inject_noise(r: random.Random, signal: str) -> tuple[str, list]:
    """Randomly sprinkle 0-2 noise sentences around the signal.
    Distribution: 50% none, 30% one, 20% two.
    """
    roll = r.random()
    if roll < 0.5:
        n_noise = 0
    elif roll < 0.8:
        n_noise = 1
    else:
        n_noise = 2

    if n_noise == 0:
        return signal, []

    noise = r.sample(_NOISE_SENTENCES, k=n_noise)
    if n_noise == 1:
        # before or after, 50/50
        if r.random() < 0.5:
            return f"{noise[0]} {signal}", noise
        return f"{signal} {noise[0]}", noise
    # n_noise == 2: one before, one after
    return f"{noise[0]} {signal} {noise[1]}", noise


_REPHRASE_TEMP = 0.7
_REPHRASE_MAX_ATTEMPTS = 3


def _rephrase_with_verification(skeleton_with_noise: str, values: list) -> tuple[str, bool, int]:
    """Ask the LLM to rephrase. Verify every value is present (word-boundary).
    Retry up to _REPHRASE_MAX_ATTEMPTS times. If still missing any value,
    fall back to skeleton_with_noise.
    Returns (statement, used_fallback, attempts_made).
    """
    last_rephrased = None
    for attempt in range(1, _REPHRASE_MAX_ATTEMPTS + 1):
        try:
            rephrased = chat(REPHRASE_SYSTEM, skeleton_with_noise, temperature=_REPHRASE_TEMP)
        except Exception:
            return skeleton_with_noise, True, attempt
        last_rephrased = rephrased
        if all(_match(v, rephrased) for v in values):
            return rephrased, False, attempt
    return skeleton_with_noise, True, _REPHRASE_MAX_ATTEMPTS


def make_case(seed: int, scenario_name: str | None = None) -> SplitIntakeCase:
    r = random.Random(seed)
    scenario_name = scenario_name or r.choice(list(SCENARIOS.keys()))
    scenario = SCENARIOS[scenario_name]
    persona = r.choice(PERSONA_NAMES)

    picked = _pick_values(r, scenario_name, scenario)
    skeleton = scenario["skeleton"].format(persona=persona, **picked)
    skeleton_with_noise, noise = _inject_noise(r, skeleton)
    user_statement, used_fallback, n_attempts = _rephrase_with_verification(
        skeleton_with_noise, list(picked.values())
    )

    per_detail_probes = [
        {
            "key": k,
            "question": scenario["probes"][k].format(persona=persona),
            "expected": v,
        }
        for k, v in picked.items()
    ]
    aggregate_probe = {
        "question": (
            f"Tell me everything {persona} mentioned. For each of the following, "
            f"give the specific value: " + ", ".join(scenario["keys"]) + "."
        ),
        "expected_by_key": dict(picked),
    }

    return SplitIntakeCase(
        case_id=f"T4-{seed:04d}",
        scenario=scenario_name,
        persona=persona,
        ground_truth_details=dict(picked),
        skeleton_statement=skeleton,
        skeleton_with_noise=skeleton_with_noise,
        user_statement=user_statement,
        noise_sentences=noise,
        used_fallback=used_fallback,
        n_rephrase_attempts=n_attempts,
        per_detail_probes=per_detail_probes,
        aggregate_probe=aggregate_probe,
    )


def generate(n: int, out_path: Path, seed: int = 0) -> None:
    cases = [make_case(seed + i) for i in range(n)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([c.to_dict() for c in cases], indent=2, ensure_ascii=False))
