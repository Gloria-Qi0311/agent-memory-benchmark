# T4 — Split Intake: Findings (n=100)

## Headline

> **On the "user says one dense statement, memory must surface each detail" task, mem0 (the most-starred OSS memory library) recalls 56% of details. A 30-line markdown baseline recalls 95%. The gap is 40 percentage points and is statistically robust at n=100 (95% bootstrap CI: mem0 [0.50, 0.61], naive [0.93, 0.97]; intervals do not overlap).**

![T4 Results](./t4_results.png)

## What this task measures

Each case is a single user statement (2-4 sentences) containing **12-13 atomic details** about the speaker — e.g. dev setup hardware/software, travel plans, home-office gear. After the memory system writes the statement, the runner asks **13 per-detail questions** ("What laptop does Alex use?") and **one aggregate question** ("Tell me everything Alex mentioned"). A detail is a hit if its ground-truth value appears (word-boundary, case-insensitive) in the reader's answer.

The point is mem0's stated value-add: **extracting structured facts from natural-language intake**. If mem0 can't reliably surface details a user explicitly mentioned, the rest of its features sit on a shaky foundation.

## Results table

| System | per-detail recall | 95% CI | aggregate recall | 95% CI |
|---|---|---|---|---|
| `no_memory` | 0.00 | — | 0.00 | — |
| `naive_markdown` | **0.952** | [0.931, 0.969] | **0.968** | [0.951, 0.982] |
| `long_context` | **0.953** | [0.933, 0.970] | **0.970** | [0.953, 0.984] |
| **`mem0`** | **0.555** | [0.498, 0.611] | **0.562** | [0.488, 0.633] |

`naive_markdown` and `long_context` are statistically indistinguishable — agent attribution tags carry no signal on this task.

## Per-scenario breakdown

All three scenarios discriminate the systems similarly:

| | dev_setup (n=38) | home_office (n=32) | travel_plan (n=30) |
|---|---|---|---|
| naive_markdown per_detail | 1.000 | 0.951 | 0.892 |
| mem0 per_detail | 0.577 | 0.583 | 0.497 |

The gap is consistent across scenario types, not driven by a quirk of any one fact pool.

## How failures differ (the more important finding)

When `mem0` and `naive_markdown` miss a detail, they miss in **qualitatively different ways**:

| Failure mode | naive_markdown | mem0 |
|---|---|---|
| `"unknown"` — system surfaced nothing | **62%** | 33% |
| Wrong concrete value — hallucinated from the same category pool | 38% | **67%** |

`naive_markdown` mostly admits ignorance. `mem0` mostly **fabricates a plausible-sounding wrong value** drawn from the same category. For a downstream user, "I don't know" and "the user uses Tower" (when they actually use lazygit) are not equivalent failures — the second is silently misleading.

## Case study: T4-0149

User statement (one of mem0's lowest-scoring cases):

> *"Bao just finished rebuilding their dev setup. They're running Arch Linux on a ThinkPad X1 Carbon Gen 12 with 48GB RAM and a 2TB SSD, paired with a Studio Display 5K and a Keychron Q3 Pro. Their software stack includes fish as the shell, JetBrains Rider as the primary IDE, and Ghostty as the terminal, with Cascadia Code for the coding font and Catppuccin Mocha for the theme. For tooling, they manage packages with Homebrew and use Tower as their git client."*

13 details, all explicitly stated. mem0's per-detail answers:

| key | ground truth | mem0's answer | result |
|---|---|---|---|
| laptop | ThinkPad X1 Carbon Gen 12 | **MacBook Pro M4 Max** | ✗ hallucinated |
| ram | 48GB | 48GB | ✓ |
| storage | 2TB SSD | 2TB SSD | ✓ |
| display | Studio Display 5K | **Pro Display XDR** | ✗ hallucinated |
| keyboard | Keychron Q3 Pro | Keychron Q3 Pro | ✓ |
| os | Arch Linux | **Fedora 41** | ✗ hallucinated |
| shell | fish | fish | ✓ |
| ide | JetBrains Rider | **Zed** | ✗ hallucinated |
| terminal | Ghostty | **WezTerm** | ✗ hallucinated |
| font | Cascadia Code | Cascadia Code | ✓ |
| theme | Catppuccin Mocha | **One Dark** | ✗ hallucinated |
| package_mgr | Homebrew | **Nix** | ✗ hallucinated |
| git_client | Tower | unknown | ✗ |

5/13 correct. The 7 wrong-value misses are not random noise — every one of them is a different value drawn from the same category's pool. This is the failure signature of mem0's extraction step silently dropping detail-rich content into a sparser internal representation, with the reader then filling gaps by plausible guess.

## Statistical methods

- **n**: 100 cases, generated programmatically with seeds 100-199 (smoke run used seeds 0-9, no overlap).
- **Probes per case**: 13 per-detail + 1 aggregate = ~14 reader LLM calls per case per system.
- **Bootstrap CI**: 10,000 resamples, 95% percentile interval.
- **Judge**: programmatic word-boundary substring match. Each ground-truth value's lowercased form must appear as a `\b<value>\b` regex match in the reader's lowercased answer. No LLM judging — this metric is reproducible bit-for-bit by anyone running the same case file.

## Limitations

1. **One reader LLM (DeepSeek-V3)**. Both naive's reading and mem0's reading use the same model; we did not test cross-vendor.
2. **mem0's internal LLM is also DeepSeek**. mem0 in production with GPT-4o-mini or Claude Haiku as its internal extraction model likely scores better than 0.56. This benchmark does not isolate "mem0 architecture" from "mem0 + cheap-LLM extractor" — that's a future experiment. The reported number is mem0 in a real-world cost-conscious deployment, which is the most common configuration.
3. **Atomic ground truth**. T4 measures *detail retention*, not the higher-order capabilities (compound update, surgical edit, cross-memory) that T2/T1/T3 will measure. mem0's value-add may surface on those tasks.
4. **Scenarios are programmatic**. Three scenarios × ~7 value pools each. Real user statements have wider variety; whether mem0's failure pattern holds on natural-distribution intake (e.g. sampled from real ChatGPT memory logs) is an open question.

## Reproducing

```bash
# Generate the same 100 cases
python scripts/generate_cases.py --task split_intake --n 100 --seed 100

# Run the experiment
python scripts/run_split_intake.py \
    --cases data/cases/split_intake_n100_s100.json \
    --systems no_memory naive_markdown long_context mem0 \
    --tag t4-prod-n100

# Inspect failure modes
python scripts/analyze_t4.py

# Re-render the plot
python scripts/plot_t4.py
```

Case file and full per-case results JSON are committed to the repo (`data/cases/split_intake_n100_s100.json`, `data/results/t4-prod-n100.json`).
