# T4 — Split Intake: Findings (n=300)

## Headline

> **Across five memory systems tested on 300 dense user statements (each bundling 12–13 atomic details), the four "extraction-free" systems (naive markdown, pure vector, and AMH — the only explicitly multi-agent-native system) cluster tightly at 0.95 per-detail recall. mem0, the only system that inserts an LLM extraction step, trails at 0.43 per-detail recall — a 52-percentage-point gap. 95% bootstrap CI intervals do not overlap. The finding is unambiguous: on this task LLM extraction — not memory architecture — is the primary source of information loss.**

![T4 Results](./t4_results.png)

## What this task measures

Each case is a single user statement (2–4 sentences) containing **12–13 atomic details** about the speaker — dev setup hardware/software, travel plans, home-office gear. The memory system writes the statement, then the runner asks **13 per-detail questions** ("What laptop does Alex use?") and **one aggregate question** ("Tell me everything Alex mentioned"). A detail is a hit if its ground-truth value appears (word-boundary, case-insensitive) in the reader's answer.

The point is to isolate what a memory system *does with intake*:
- naive_markdown / pure_vector: **store raw, retrieve raw** — the reader LLM re-extracts details at read time.
- AMH: **store raw markdown entries, retrieve by keyword scoring** — no LLM inside, but structured shared-memory model.
- mem0: **LLM extracts facts at write time**, retrieves by vector similarity — the reader sees mem0's *summary of the input*, not the input itself.

## The five systems under test

| System | Storage | Extraction step | Retrieval | Category |
|---|---|---|---|---|
| `no_memory` | — | — | — | Floor |
| `naive_markdown` | Verbatim, in-memory list | None | Return all entries | Engineer's DIY |
| `pure_vector` | Verbatim + embeddings | None | Cosine top-K | Engineer's DIY |
| `amh` | Verbatim in Markdown files | None | Keyword scoring | **Multi-agent-native** |
| `mem0` | LLM-extracted fact list | Yes, `deepseek-chat` | Vector top-K | Single-agent, repurposed |

## Results (n=300)

| System | per-detail recall | 95% CI | aggregate recall | 95% CI |
|---|---|---|---|---|
| `no_memory` | 0.000 | — | 0.000 | — |
| `naive_markdown` | **0.951** | [0.943, 0.958] | **0.968** | [0.963, 0.973] |
| `pure_vector` | **0.951** | [0.944, 0.958] | **0.969** | [0.964, 0.974] |
| `amh` | **0.950** | [0.943, 0.957] | **0.969** | [0.964, 0.974] |
| **`mem0`** | **0.432** | [0.399, 0.466] | **0.555** | [0.511, 0.599] |

The three extraction-free systems are statistically indistinguishable — their CIs overlap almost entirely. **mem0's CI (per-detail [0.399, 0.466]) does not overlap any of them.**

## Per-scenario breakdown

The pattern holds across all three scenarios; travel_plan is uniformly the hardest for every system, but the ordering never changes:

| Scenario (n) | naive_markdown pd | pure_vector pd | amh pd | mem0 pd |
|---|---|---|---|---|
| dev_setup (n=113) | 1.000 | 1.000 | 1.000 | **0.453** |
| home_office (n=91) | 0.948 | 0.948 | 0.948 | **0.467** |
| travel_plan (n=96) | 0.895 | 0.897 | 0.894 | **0.374** |

## How failures differ

When each system misses a detail, it misses in a **qualitatively different way**:

| Failure mode | naive_markdown | pure_vector | amh | mem0 |
|---|---|---|---|---|
| `"unknown"` — system surfaced nothing | 54.5% | 50.6% | 51.4% | 45.9% |
| Wrong concrete value — hallucinated from category pool | 45.5% | 49.4% | 48.6% | **54.1%** |
| Total per-detail misses (out of 300 × 13 probes) | 178 | 176 | 179 | **2107** |

Two things to notice:

1. **mem0 fails an order of magnitude more often** than the extraction-free systems (2107 vs ~178 missed probes) — this is the 52-point recall gap re-expressed as failure count.
2. **mem0 fails wrong more often than it fails silent.** When the extraction-free systems can't surface a value, they roughly split between "unknown" and hallucinating a same-category alternative. mem0 tilts toward hallucinating — because the reader is looking at mem0's *summary*, not the source, and confidently completes plausible-looking gaps.

For a downstream user, `"unknown"` and `"the user uses fish"` (when they actually use bash) are not equivalent failures. The second is silently misleading.

## Case study: T4-0385

A representative failure. All three extraction-free systems scored ≥ 0.85 on this case; mem0 scored **0/13**.

User statement:
> *"Hana just rebuilt their dev setup around a Framework 13 with 64GB of RAM and a 1TB SSD, paired with an LG UltraFine 5K display and a HHKB Studio keyboard. On the software side, they run Fedora 41 with bash as their shell, Zed as their primary IDE, and Alacritty as their terminal. The look is Berkeley Mono for the coding font and Tokyo Night for the theme. For tooling, they manage packages with apt and use GitHub Desktop as their git client."*

13 details, all stated explicitly. mem0's per-detail answers side by side with ground truth:

| key | ground truth | mem0's answer | verdict |
|---|---|---|---|
| laptop | Framework 13 | unknown | ✗ |
| ram | 64GB | unknown | ✗ |
| storage | 1TB SSD | unknown | ✗ |
| display | LG UltraFine 5K | **Studio Display 5K** | ✗ hallucinated |
| keyboard | HHKB Studio | **ZSA Voyager** | ✗ hallucinated |
| os | Fedora 41 | unknown | ✗ |
| shell | bash | **fish** | ✗ hallucinated |
| ide | Zed | unknown | ✗ |
| terminal | Alacritty | unknown | ✗ |
| font | Berkeley Mono | unknown | ✗ |
| theme | Tokyo Night | unknown | ✗ |
| package_mgr | apt | unknown | ✗ |
| git_client | GitHub Desktop | **GitKraken** | ✗ hallucinated |

Zero correct. Four of the misses are hallucinated same-category values — mem0's LLM extraction step produced a lossy summary of "Hana uses [things]", and when the reader was asked about specific values, it filled the gaps from the same category's pool (fish is a shell, GitKraken is a git client, ZSA Voyager is a keyboard, Studio Display 5K is a display). The pattern is: **mem0 knows the *category* Hana talked about but not the actual *value* Hana chose.**

## Product implications

The result cluster is unambiguous: **on this task, the presence of an LLM extraction step (mem0) is the dominant loss source**, not any specific storage or retrieval architecture. Vector search vs keyword scoring vs verbatim didn't matter — extraction vs no extraction was the split.

For teams building multi-agent products where memory needs to preserve concrete details:

1. **Default to storing raw utterances**, at least until context-window pressure makes it infeasible. LLM extraction is a compression step whose loss profile is non-obvious.
2. **If you need retrieval to be more than dump-everything**, prefer non-LLM retrieval (keyword or vector) before adopting LLM extraction. Both give equivalent recall on this task at zero LLM-inference cost per write.
3. **Silent hallucination is the failure mode to watch**. Systems with LLM extraction don't fail loudly — they fail by supplying plausible wrong values. Any product using such a memory system needs downstream guards (verification, source citation, or user confirmation).

The **AMH result** is worth noting separately. It's the only system architecturally designed for multi-agent shared memory, and its extraction-free implementation lands in the same cluster as generic engineer DIY. Being purpose-built for multi-agent doesn't automatically produce better single-write information preservation — but it doesn't hurt either. The value-add of a multi-agent-native design will likely surface on the T2 (compound update) and T3 (cross-memory) tasks, where a system's ability to reconcile writes across sessions and agents matters. T4 alone doesn't stress that.

## Statistical methods

- **n**: 300 cases total. Two case files with disjoint seed ranges: 100 cases at seeds 100–199, 200 cases at seeds 200–399. Committed at `data/cases/split_intake_n100_s100.json` and `data/cases/split_intake_n200_s200.json`.
- **Probes per case**: 13 per-detail + 1 aggregate = ~14 reader LLM calls per case per system.
- **Bootstrap CI**: 10,000 resamples, 95% percentile interval.
- **Judge**: programmatic word-boundary substring match (`\b<value>\b`) between each ground-truth value and the reader's answer, both lowercased. No LLM judging — reproducible bit-for-bit.

## Limitations

1. **One reader LLM (DeepSeek-V3).** Every system's reader uses the same model, so cross-vendor generalization is not tested.
2. **mem0's internal LLM is DeepSeek-chat.** mem0 with GPT-4o-mini or Claude Haiku as its internal extractor likely scores better than 0.43. This benchmark reports mem0 in a cost-conscious deployment (the most common configuration), not mem0 at its best.
3. **T4 measures single-write detail retention only.** Compound update (T2), surgical edit (T1), and cross-memory consolidation (T3) are not covered here. mem0's or AMH's value-add may surface on those tasks.
4. **Three scenarios, programmatic generation.** Natural-distribution intake (sampled from real ChatGPT-memory-style logs) is a future test.
5. **AMH is developed by a personal contact of the author.** To avoid conflict of interest: the AMH repo used is a fork at a pinned state with no code modifications; AMH is treated on identical footing with the other four systems (same runner, same probes, same judge); and the finding places AMH in a statistical cluster with `naive_markdown` and `pure_vector` rather than singling it out.

## Reproducing

```bash
# Generate both case files (disjoint seed ranges)
python scripts/generate_cases.py --task split_intake --n 100 --seed 100
python scripts/generate_cases.py --task split_intake --n 200 --seed 200

# Run experiments (each ~1-2 hours on DeepSeek-V3)
python scripts/run_split_intake.py \
    --cases data/cases/split_intake_n100_s100.json \
    --systems no_memory naive_markdown pure_vector amh mem0 \
    --tag t4-repro-n100-5sys
python scripts/run_split_intake.py \
    --cases data/cases/split_intake_n200_s200.json \
    --systems no_memory naive_markdown pure_vector amh mem0 \
    --tag t4-repro-n200-5sys

# Merge the two runs into a single n=300 view
python scripts/merge_t4_runs.py \
    --inputs data/results/t4-repro-n100-5sys.json \
             data/results/t4-repro-n200-5sys.json \
    --out /tmp/t4-repro-n300-merged.json

# Failure-mode + per-scenario breakdown
python scripts/analyze_t4.py --results /tmp/t4-repro-n300-merged.json

# Case-study picker
python scripts/pick_case_study.py \
    --results /tmp/t4-repro-n300-merged.json \
    --cases data/cases/split_intake_n100_s100.json \
            data/cases/split_intake_n200_s200.json

# Re-render the plot
python scripts/plot_t4.py --results /tmp/t4-repro-n300-merged.json
```

The final merged raw per-case result is committed in
`data/results/t4-prod-n300-merged.json`. The two batch files used during the
original run are temporary reproduction artifacts and are not committed.
