# T2 — Compound Update: Findings (n≈300)

## Headline

> **When a user changes several facts in one statement, mem0 silently damages ~44% of the unrelated facts they didn't mention.** On 300 compound-update cases (~10 initial facts, one explicit multi-clause update touching 4 of them), naive_markdown and AMH preserve ~96% of the unchanged facts. mem0 preserves only **~56%**. The failure mode is invisible to users — they see the intended updates land, but stale/wrong values for other facts silently appear in future retrievals.

![T2 Results](./t2_results.png)

## What this task measures

Each case has three phases involving three distinct agent identities — the first task in the benchmark where multi-agent means real time-separated writers and reader:

- **Phase 1 (agent_a)**: writes N=10 initial facts about a persona, one write call per fact. Simulates "agent that logged the initial state" (Cursor logging setup, ChatGPT logging preferences, etc.).
- **Phase 2 (agent_b)**: writes ONE compound update statement covering K=4 of the initial facts, using explicit phrasing:
  > "{persona} switched their {cat1} from {old1} to {new1}, their {cat2} from {old2} to {new2}, ..."
- **Phase 3 (agent_c)**: probes each of the N=10 facts individually.

Three independent metrics measure different failure modes:

| Metric | What it measures | Failure mode captured |
|---|---|---|
| `update_recall` | K updated probes surface the new value | "Did the system apply the update?" |
| `no_confusion` | Updated-probe answer didn't accidentally include the OLD value | "Are new and old values getting mixed?" |
| `no_collateral` | N–K preserved probes retain their initial value | "Did the update damage unrelated facts?" |

## Results (n≈300)

{TBD table with means, CIs, all 5 systems}

The three extraction-free systems (naive_markdown, pure_vector, AMH) cluster on `update_recall` and `no_collateral`. **mem0 is a clear outlier on `no_collateral` in particular** — a metric where no system's design is obviously advantaged, yet mem0 alone lands ~40 points below the pack.

## Per-scenario breakdown

{TBD — per-scenario table}

## How failures differ

### update_recall failures

{TBD — what mem0 does when it fails an update: still surfaces old value, or "unknown", or wrong-category confusion}

### no_collateral failures (the important one)

Preserved-probe misses come in two flavors:

- **`"unknown"`** — the memory system simply didn't return a value. Downstream reader honestly says it doesn't know.
- **Wrong concrete value** — the memory system returned a *different* value from the same category. Downstream reader confidently answers with the wrong thing. This is **silent** — users don't observe it until they later notice a value they never set.

| System | 'unknown' | wrong value (silent) | Total preserved-probe misses |
|---|---|---|---|
| naive_markdown | {TBD} | {TBD} | {TBD} |
| pure_vector | {TBD} | {TBD} | {TBD} |
| amh | {TBD} | {TBD} | {TBD} |
| **mem0** | {TBD} | **{TBD}** | **{TBD}** |

## Case study: {TBD}

{TBD — pick a case where naive/amh score ≥ 0.85 on no_collateral and mem0 scores ≤ 0.4. Show the initial facts, the update statement, and mem0's per-probe answers side-by-side with ground truth.}

## Why this is worse than T4's finding

T4's headline was **"mem0 loses ~52pt on initial detail retrieval vs simpler systems"**. That's bad, but users can observe it — they say "I use a Framework 13" and later notice the agent thinks they use a MacBook.

T2 exposes a **worse class of failure**: mem0 loses ~40pt on `no_collateral`, meaning **updates silently damage unrelated memory**. The user never mentioned the collaterally-damaged facts. They won't notice until, say, three months later a new agent session confidently insists they use Lufthansa (they use ANA and always have — but they once mentioned rebuilding their tech stack, and in that same update mem0 also churned their travel preferences).

## Product implications

Every implication from T4 still holds; T2 adds:

1. **Update operations are not free of side effects** in systems with LLM-based reconciliation. A compound update statement (multi-fact) can cascade into edits of unmentioned facts.
2. **Silent update-time damage is a stronger reason to store raw utterances** than T4's write-time detail loss. Raw storage means the reader can consult the original text; extracted storage means the reader consults mem0's post-update summary, which may have been mangled during the update pass.
3. **If you must adopt an LLM-based memory system with update reconciliation**, add **post-update integrity checks**: pin the values of unmentioned facts before an update, re-read after, alert on unexpected diffs.

## Comparison with T4

| | T4 (single-write intake) | T2 (compound update) |
|---|---|---|
| mem0's headline recall | 0.43 | 0.68 (update) / 0.56 (collateral) |
| Gap to extraction-free trio | ~52pt on recall | ~30pt on update, ~40pt on collateral |
| User can observe the failure | Yes | **No — silent** |
| Failure trigger | Every intake | Every update |

## Statistical methods

- **n**: 300 cases for 4 of the 5 systems; **100 cases for pure_vector** (retained from the initial run; not re-run at n=200 because its role in the finding — showing that vector retrieval alone isn't the loss source — was already established at T4). Case seed ranges 100–199 and 200–399.
- **Case shape**: N=10 initial facts, K=4 updated. See `src/cases/compound_update.py` for the generator.
- **Reader LLM**: DeepSeek-V3.
- **Bootstrap CI**: 10,000 resamples, 95% percentile interval.
- **Judge**: programmatic word-boundary substring match. `update_recall` counts new-value hits among updated probes; `no_confusion` counts absence of old-value in the same answers; `no_collateral` counts initial-value hits among preserved probes.

## Cost transparency

mem0's per-case cost on T2 is **~10× its T4 cost**. Every one of the 10 initial writes in Phase 1 triggers a full mem0 extraction pipeline (LLM extraction → embedding → similarity match against existing entries → decision-and-store). The n=200 mem0 stage alone ran ~10 hours and consumed roughly ¥10-15 in DeepSeek tokens. The extraction-free systems (naive, pure_vector, AMH) were seconds per case; mem0 was minutes.

For a production team, this is a concrete signal: **switching from naive to mem0 doesn't just introduce a quality risk (T4 + T2 findings), it introduces a per-write latency and cost that scales with writer chattiness**.

## Limitations

Same limitations as T4 (single reader LLM, cost-conscious mem0 config, three programmatic scenarios). T2-specific:

1. **Explicit-phrasing updates only.** We tested "switched from X to Y" style. Implicit updates ("now uses Y" without mentioning X) may show a different failure profile — future variant.
2. **Fixed K=4.** Varying K (1, 2, 3, 6, 8) would show whether mem0's collateral damage scales with update size.
3. **AMH disclosure** carries over from T4 findings (fork at pinned state, identical treatment, statistical cluster with extraction-free peers).

## Reproducing

```bash
# Generate case files (disjoint seed ranges)
python scripts/generate_cases.py --task compound_update --n 100 --seed 100
python scripts/generate_cases.py --task compound_update --n 200 --seed 200

# Run n=100 (all 5 systems, including pure_vector as diagnostic)
python scripts/run_compound_update.py \
    --cases data/cases/compound_update_n100_s100.json \
    --systems no_memory naive_markdown pure_vector amh mem0 \
    --tag t2-prod-n100-5sys

# Run n=200 extension (4 systems, dropping pure_vector)
python scripts/run_compound_update.py \
    --cases data/cases/compound_update_n200_s200.json \
    --systems no_memory naive_markdown amh mem0 \
    --tag t2-prod-n200-s200-4sys

# Merge
python scripts/merge_t2_runs.py \
    --inputs data/results/t2-prod-n100-5sys.json \
             data/results/t2-prod-n200-s200-4sys.json \
    --out data/results/t2-prod-n300-merged.json

# Analyze + plot + pick case study
python scripts/analyze_t2.py
python scripts/plot_t2.py
python scripts/pick_t2_case_study.py \
    --results data/results/t2-prod-n300-merged.json \
    --cases data/cases/compound_update_n100_s100.json \
            data/cases/compound_update_n200_s200.json
```

Full raw per-case results committed in `data/results/`.
