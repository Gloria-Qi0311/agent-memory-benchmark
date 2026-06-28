# Roadmap

A living checklist. Keep it short. When something moves to `done`, that's a commit-worthy milestone.

## Done

- Scaffold: case generator, judge, runner, three system adapters (`no_memory`, `naive_markdown`, `mem0`).
- Public GitHub repo, CI-free for now.
- First head-to-head results on **n=5 fusion cases** with DeepSeek-V3:
  - `no_memory` 0.00 (floor anchored)
  - `naive_markdown` 1.00 (ceiling anchored)
  - `mem0` 0.95 (preliminary signal — industry default trailing the naive baseline)
- Local sentence-transformers model checked in via manual download (HF library path blocked by SSL/HEAD issues on this machine).
- Python 3.11 baseline established; documented in `docs/decisions.md`.

## Now (this is what to pick up next session)

- **Make the fusion task harder so signal can emerge.** At n=5 with current settings, both `naive_markdown` and `mem0` saturate at 1.00. Options to add difficulty:
  - More facts per persona (currently 4, try 8–12).
  - Filler turns between agent A's writes and agent B's writes (so memory has to survive noise).
  - Phrase the probe question without naming categories (forces the system to actually understand, not pattern-match).
- **Scale to n=100** once the task discriminates. ~$0.20 in DeepSeek API.
- **Eyeball failure cases.** Once at least one system drops below 1.00, read 5–10 misses by hand to find the qualitative story.
- **First plot.** Matplotlib bar chart of `mean_recall` per system with per-case dots and error bars. PNG checked into `docs/`.

## Next

- **Rewrite-preservation task** (`src/cases/rewrite.py`). Auxiliary signal: when one fact is updated, what fraction of the other N-1 facts survive?
- **README rewrite**. Lead with the finding, follow with method, finish with implications. (Now is too placeholder.)
- **Add a 4th system**: either `Letta` or `mem0 Platform` (the hosted version) — broadens the comparison. Pick whichever is faster to integrate.

## Parking lot (don't do yet)

- Streamlit dashboard. Wait until at least two tasks × four systems × 100 cases exist; before that, a dashboard would have nothing to show.
- Multi-LLM-vendor experiment (Claude writes, GPT reads). Interesting but expensive. Defer until the single-LLM story is rock solid.
- Conflict resolution as a standalone task. Subsumed for now by the fusion task plus future rewrite task.
- Anything called "leaderboard". Implies more systems than v1 has — would inflate scope.
- spaCy install for mem0. Currently noisy warning, but not breaking. Skip until it actually blocks something.

## Open questions

- **Self-evaluation bias from DeepSeek-only.** Document this in the README before publishing the n=100 number. Possibly add one robustness check (50 cases re-judged by a different model) before scaling further.
- **n=100 confidence**. With recall scores tightly clustered around 1.0, a 5% delta might disappear into noise. Consider also reporting per-case "did mem0 miss any facts at all" — a binary metric is more robust at the ceiling.
