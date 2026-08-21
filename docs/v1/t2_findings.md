# T2 — Compound Update: corrected analysis

## Current status

The judge and ground-truth audit are complete for the stored T2 answers. The
results for `no_memory`, `naive_markdown`, `pure_vector`, and `AMH` can be
reported. The historical `mem0` rows are retained for diagnosis but are **not
publishable**: those runs predate full clearing of mem0's recent-message SQLite
state between cases and therefore may contain cross-case contamination. mem0
must be rerun with the corrected adapter before a five-system comparison is
final.

No DeepSeek calls were required for the corrected scoring. The reader answers
and memory contexts already stored in the result files were judged again.

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
| mem0 (historical, invalid run) | 298 | 0.584 | 0.896 | 0.489 |

The first four rows are corrected reportable scores. Confidence intervals are
deterministic case-level percentile bootstrap intervals with 10,000 resamples.
The mem0 values are shown only so old files remain interpretable; they are not
evidence until an isolated rerun replaces them.

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

## Why historical mem0 must be rerun

The old adapter cleared vector memories between T2 cases but did not clear
mem0's recent-message SQLite table. mem0 uses those recent messages as
extraction context. Since every case used the same benchmark user scope, later
cases could receive utterances from earlier cases during extraction.

The adapter now calls mem0's full `reset()`, clearing vector state and SQLite
message/history state. The database also lives in the adapter's isolated
temporary directory.

Until the mem0-only rerun finishes, the defensible conclusion is:

> On 298 valid compound-update cases, naive_markdown almost perfectly applied
> explicit updates and preserved unrelated facts. AMH preserved unrelated facts
> equally well but applied fewer intended updates. A valid mem0 comparison is
> pending an isolated rerun.

## Reproducing the corrected scoring

```bash
python scripts/rescore_t2.py \
  --results data/results/t2-prod-n100-5sys.json \
  --cases data/cases/compound_update_n100_s100.json \
  --out data/results/t2-prod-n100-5sys.json

python scripts/rescore_t2.py \
  --results data/results/t2-prod-n200-s200-4sys.json \
  --cases data/cases/compound_update_n200_s200.json \
  --out data/results/t2-prod-n200-s200-4sys.json

python scripts/merge_t2_runs.py \
  --inputs data/results/t2-prod-n100-5sys.json \
           data/results/t2-prod-n200-s200-4sys.json \
  --out data/results/t2-prod-n300-merged.json

python scripts/analyze_t2.py --results data/results/t2-prod-n300-merged.json
```

Result metadata records the judge version, excluded cases, changed probe
judgments, zero LLM calls for rescoring, and the invalid historical mem0 status.
