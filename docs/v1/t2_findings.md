# T2 — Compound Update: corrected analysis

## Current status

The judge and ground-truth audit are complete. Historical mem0 rows that
predated full recent-message isolation were discarded and replaced by a clean
mem0-only rerun. All five systems now have reportable results. Existing reader
answers were locally rejudged; only the replacement mem0 run called DeepSeek.

## What T2 measures

Each case simulates three agents and one shared memory:

1. `agent_a` writes ten initial facts, one per call.
2. `agent_b` writes one sentence that explicitly updates four facts.
3. `agent_c` independently asks about all ten facts.

| Metric | Product question |
|---|---|
| `update_recall` | Did the four intended new values become answerable? |
| `no_confusion` | Did answers avoid surfacing the corresponding old value? |
| `no_collateral` | Did the six unmentioned facts remain answerable? |

`no_confusion` is not accuracy by itself: `unknown` contains no old value and
therefore passes this metric while failing `update_recall`.

## Corrected results

Two invalid authored cases were excluded, leaving n=298 for systems run on both
batches. `pure_vector` was only run in the first batch and has n=99.

| System | n | Update recall, 95% CI | No confusion, 95% CI | No collateral, 95% CI |
|---|---:|---:|---:|---:|
| no_memory | 298 | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| naive_markdown | 298 | **0.999** [0.997, 1.000] | **0.997** [0.993, 0.999] | 0.978 [0.971, 0.985] |
| pure_vector | 99 | 0.886 [0.851, 0.919] | 0.907 [0.874, 0.937] | **0.983** [0.973, 0.992] |
| AMH | 298 | 0.893 [0.876, 0.909] | 0.909 [0.893, 0.924] | 0.978 [0.971, 0.985] |
| mem0 | 298 | 0.976 [0.966, 0.985] | 0.981 [0.971, 0.988] | 0.961 [0.952, 0.970] |

All rows are reportable. Confidence intervals are deterministic case-level
percentile bootstrap intervals with 10,000 resamples. pure_vector's n=99
diagnostic result should not be read as having the same precision as n=298.

The main result is that mem0 performs well once benchmark state is correctly
isolated: its update recall is 0.976 and its no-collateral score is 0.961. It
trails naive_markdown by 2.3 points on updates and 1.7 points on preservation,
while outperforming AMH by 8.3 points on updates. The confidence intervals for
mem0 and naive overlap slightly on no-collateral but do not overlap on update
recall.

## Judge corrections

### Token boundaries

The old matcher used Python's `\b`. It incorrectly rejected exact answers that
ended in punctuation-like product-name characters:

```text
expected: SSL 2+
answer:   SSL 2+.
old result: miss
new result: hit
```

The new matcher prevents `Go` from matching `going`, while accepting exact
names containing `+`, `.`, `-`, or `/`.

### Authored accepted answers

T2 remains deterministic exact matching, not fuzzy similarity or an LLM judge.
One field needed explicit accepted forms because its stored value and question
use different grammar:

| Ground-truth value | Accepted answers |
|---|---|
| `with family` | `with family`, `family` |
| `with their partner` | `with their partner`, `their partner`, `partner` |
| `with colleagues` | `with colleagues`, `colleagues` |
| `solo` | `solo`, `alone` |

Storage answers also accept the authored word-order equivalent, for example
`4TB SSD` and `4TB of SSD storage`.

Aliases are field-specific; they do not make matching generally fuzzy.

## Ground-truth audit

All 310 committed T2 case artifacts (10 smoke + 100 + 200 production) were
checked programmatically for one probe per fact, unique keys, real old-to-new
changes, presence of every old/new value in the update sentence, and correct
updated/preserved probe labels.

Two production cases failed:

| Case | Invalid authored update |
|---|---|
| `T2-0104` | OS: `Arch Linux` → `Arch Linux` |
| `T2-0255` | OS: `Ubuntu 24.04` → `Ubuntu 24.04` |

The full cases were excluded instead of rewriting truth after the model had
already seen them. Laptop/OS compatibility logic caused the bug by overwriting
a selected new OS with the original OS. That branch and a similar single-date
no-op branch are fixed. Six hundred generated seeds now pass validation.

## Why mem0 was rerun

The old adapter cleared vector memories between T2 cases but did not clear
mem0's recent-message SQLite table. mem0 uses those recent messages as
extraction context. Since every case used the same benchmark user scope, later
cases could receive utterances from earlier cases during extraction.

The adapter now calls mem0's full `reset()`, clearing vector state and SQLite
message/history state. The database also lives in the adapter's isolated
temporary directory. A 10-case gate passed before the two production batches;
the 99-case and 199-case runs both completed with zero runtime errors.

The correction materially changed the product conclusion. The contaminated
historical mem0 run scored 0.584 update recall and 0.489 no-collateral after
judge correction. The isolated replacement scored 0.976 and 0.961. The old
numbers measured benchmark leakage, not mem0's T2 capability.

The defensible conclusion is:

> On explicit compound updates, naive_markdown is nearly perfect, mem0 is a
> close second and substantially stronger than AMH at applying updates, and
> all three preserve unmentioned facts at roughly 96–98%. Correct per-case
> state isolation is necessary for any mem0 comparison.

## Reproducing the corrected scoring

The committed artifact is the final merged result. The commands below show
how to reproduce it from the committed case files; batch outputs are local
temporary files and are intentionally not committed.

```bash
# Run clean, per-case-isolated mem0 batches (the runner excludes the two
# invalid cases). Use temporary output names if reproducing locally.
python scripts/run_compound_update.py \
  --cases data/cases/compound_update_n100_s100.json \
  --systems mem0 --tag t2-repro-n100-mem0-isolated

python scripts/run_compound_update.py \
  --cases data/cases/compound_update_n200_s200.json \
  --systems mem0 --tag t2-repro-n200-mem0-isolated

# Run the complete five-system batches, then merge the temporary outputs.
python scripts/run_compound_update.py \
  --cases data/cases/compound_update_n100_s100.json \
  --systems no_memory naive_markdown pure_vector amh mem0 \
  --tag t2-repro-n100-5sys

python scripts/run_compound_update.py \
  --cases data/cases/compound_update_n200_s200.json \
  --systems no_memory naive_markdown pure_vector amh mem0 \
  --tag t2-repro-n200-s200-5sys

python scripts/merge_t2_runs.py \
  --inputs data/results/t2-repro-n100-5sys.json \
           data/results/t2-repro-n200-s200-5sys.json \
  --out /tmp/t2-prod-n300-merged.json

python scripts/analyze_t2.py --results /tmp/t2-prod-n300-merged.json
```

The committed result metadata records the judge version, case set, excluded
cases, and full per-case reset provenance. The maintenance scripts used for
the historical correction remain in `scripts/`, but their intermediate input
files are not part of the published artifact set.
