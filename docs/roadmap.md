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

- **Scale fusion to n=100**. `python scripts/generate_cases.py --task fusion --n 100` then re-run the head-to-head. Estimated cost: ~$0.20 in DeepSeek API.
  - Sanity check: does mem0's 5% deficit hold at n=100, or shrink toward parity, or widen?
- **Eyeball the failure cases**. Read 5–10 cases where `mem0` missed a fact but `naive_markdown` got it. Look for the pattern. This is the most likely place a sharp finding hides.
- **First plot**. Matplotlib bar chart of `mean_recall` per system, with error bars. One PNG checked into `docs/`.

## Next

- **Rewrite-preservation task** (`src/cases/rewrite.py`). Auxiliary signal: when one fact is updated, what fraction of the other N-1 facts survive?
- **README rewrite**. PM-style framing: lead with the finding, follow with method, finish with implications. (Now is too placeholder.)
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
