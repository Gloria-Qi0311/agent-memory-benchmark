# PM Evaluation vs. This Memory Benchmark

## Short answer

Yes, this benchmark feels different from what an evaluation PM usually does because it is operating at a narrower layer.

The PM document describes an evaluation design workflow for AI products or AI modules: define the evaluation object, clarify the ideal behavior, split dimensions, choose evidence, build cases, run evaluation, and feed findings back into product iteration.

This repository is not doing the full PM evaluation workflow. It is implementing one specific benchmark inside that workflow: a controlled, engineering-heavy module evaluation for multi-agent shared-memory systems.

## What the PM document is about

The document is about how to turn a vague request like "evaluate this AI product/module" into a usable evaluation plan.

It asks PM-style questions:

- What exactly are we evaluating: the whole product, or one AI node?
- What user/business outcome should this thing achieve?
- What bad cases must be avoided?
- Which dimensions should be scored separately?
- What observable evidence should we use?
- Do we use historical data, online data, human labels, or synthetic cases?
- How will the result guide product or prompt iteration?

So the PM artifact usually looks like:

- evaluation scope
- scenario taxonomy
- evaluation dimensions
- scoring rubric
- data plan
- labeling or judging plan
- analysis of bad cases
- iteration recommendations

## What this benchmark is doing

This repo is closer to a research/engineering benchmark. It asks a narrower question:

> When multiple agents share one memory layer, can different memory systems preserve, retrieve, and update user facts correctly?

The current tasks are intentionally synthetic and controlled:

- T4 split intake: one dense statement contains 12-13 facts; measure whether each fact can be recalled.
- T2 compound update: several facts are updated in one message; measure whether new facts land and unrelated facts survive.
- T1 surgical edit: planned test for changing one detail inside a dense memory.
- T3 cross-memory update: planned test for reconciling updates scattered across sessions.

The evidence is mostly programmatic:

- generated cases with known ground truth
- fixed probes
- exact-value matching via word-boundary substring checks
- per-system summary metrics

This makes the benchmark reproducible and comparable, but it is less like PM evaluation of a user-facing product experience.

## Main mismatch

| PM evaluation document | Current benchmark |
|---|---|
| Starts from product/user problem | Starts from memory-system capability gap |
| Defines ideal user-facing behavior | Defines low-level memory correctness |
| Splits business/product dimensions | Splits memory operations: intake, update, edit, consolidation |
| Uses real cases, synthetic cases, labels, behavior data | Mostly uses synthetic cases with known ground truth |
| Often needs qualitative rubrics | Mostly uses deterministic scoring |
| Guides product/prompt iteration | Compares memory architectures and failure modes |
| Evaluates "is this AI useful/safe/good?" | Evaluates "does this memory system preserve and reconcile facts?" |

## Better framing

The current benchmark should probably not be presented as "an AI product evaluation" in the broad PM sense.

It is better framed as:

> A module-level, capability-specific benchmark for shared-memory systems used by AI agents.

Or more concretely:

> A controlled benchmark that evaluates whether memory systems can preserve, retrieve, and update concrete user facts across multiple agents.

Under the PM document's framework, this benchmark corresponds to:

- evaluation object: memory layer / memory system adapter
- minimum evaluation unit: one memory write-read-update flow
- ideal behavior: preserve facts, update changed facts, avoid confusion and collateral damage
- evidence: generated input, retrieved context, reader answer, known ground truth
- dimensions: recall, update correctness, no confusion, no collateral damage
- evaluation type: prior/synthetic regression benchmark

## What is missing if we want it to feel more like PM evaluation

To make this feel closer to PM evaluation, add a short evaluation design layer before the engineering benchmark:

1. Product scenario

   Example: "A user works with several agents, and all agents rely on one shared memory layer to remember user preferences and project facts."

2. User impact

   Example: "Wrong memory causes agents to give stale, misleading, or inconsistent assistance."

3. Evaluation dimensions

   Keep the current engineering metrics, but map them to user-facing risks:

   - intake recall -> does the system remember what the user explicitly said?
   - update recall -> does the system learn changed preferences?
   - no confusion -> does it attach facts to the right field/entity?
   - no collateral -> does one update accidentally erase unrelated memory?
   - hallucinated wrong value rate -> does it confidently mislead the user?

4. Case taxonomy

   Make case types read like PM scenarios:

   - user gives many preferences in one message
   - user changes several preferences at once
   - user corrects one outdated detail
   - another agent asks about a fact written by a previous agent
   - project facts are scattered across different sessions

5. Decision thresholds

   Add "what result is acceptable?" For example:

   - no memory system can ship if hallucinated wrong value rate exceeds X
   - a memory system must preserve unrelated facts above Y after updates
   - regressions over Z points block release

6. Bad-case review

   Add a qualitative sample review step for high-impact failures, not only aggregate metrics.

## Bottom line

Your feeling is right.

The PM document describes the full evaluation-thinking process. This repo currently contains a rigorous benchmark artifact that would sit inside that process, after scope, dimensions, evidence, and case design have already been decided.

So the issue is not that the benchmark is wrong. It is under-wrapped from a PM perspective. It needs a PM-facing evaluation brief that explains the product scenario, user risk, evaluation dimensions, case taxonomy, and decision thresholds around the existing engineering benchmark.
