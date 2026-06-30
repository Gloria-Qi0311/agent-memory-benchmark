# v1: Non-trivial memory benchmark

## Why v1 exists (what v0 taught us)

v0 used atomic memories — each "memory" was a single fact like `"Alex uses Python as their language."`, and updates were equally atomic ("X switched to Y. They don't use Z anymore."). At that granularity the tasks turned out trivial: modern LLMs read the raw context and reason out the update without help, so `naive_markdown` (a 30-line shared list) saturates at 100% and mem0's underperformance reflects only the non-determinism of its internal extraction, not any meaningful capability difference. **v0 is a dead-end as a benchmark.**

The lesson that drove v1: **atomic memory is not what real memory systems handle**. Real memories are structured paragraphs with multiple embedded facts. Real updates touch parts of memories, multiple facts simultaneously, or span across memories. v0 didn't measure any of that — v1 does.

## v1 task types (4 levels of difficulty)

Each level exposes a different memory-system capability that v0's atomic setup hides.

### T4 — Split intake (✅ DONE)

**Headline result (n=100):** `mem0` 0.555 per-detail recall vs `naive_markdown` 0.952. Full writeup: [`t4_findings.md`](./t4_findings.md). Chart: [`t4_results.png`](./t4_results.png).

**What the user does:** Says one long thing containing N independent facts.

> "我刚买了 MacBook Pro M4 Max 64G RAM 8TB SSD，配了 Studio Display 5K + Logitech MX Master 3S，键盘 Keychron Q3 Pro 红轴，系统从 Sonoma 升到 Sequoia，主要用 Cursor + Ghostty。"

**What the memory system must do:** Decompose this into the right number of memories (or keep it whole and still answer probes about individual details).

**What we measure:** Did each of the N specific details survive — both at storage time and at probe time?

**Why this exists:** mem0's main selling point is "extract structured facts from natural language". This is the test of that capability. **If mem0 cannot reliably split intake, none of its other features matter.**

This is also where mem0 has a real chance to beat naive baselines, because a single 200-character user statement may exceed naive_markdown's ability to surface each detail under targeted retrieval (the LLM has to re-extract every read).

### T2 — Compound update (next)

**What the user does:** Says a single sentence that simultaneously updates K facts about themselves.

> "I rebuilt the stack — TypeScript + Next.js on Cloudflare, deployed via Vercel."

(Previously was Python + Django on AWS + GitHub Actions — K=4 simultaneous changes.)

**What the memory system must do:** Update all K facts. Don't update facts not mentioned. Don't conflate (assigning the TypeScript value to "framework" instead of "language").

**What we measure:**
- `update_correct@K`: did all K fact updates land correctly?
- `no_confusion`: did values get assigned to the right keys?
- `no_collateral`: were unmentioned facts left alone?

**Why this exists:** Most real "update" events in product use are not single-fact — they're compound (a user reshaping their workflow, moving to a new role, etc.). Single-fact rewrite tests don't surface whether a system can untangle several simultaneous changes.

### T1 — Surgical edit on long memory

**What the user does:** First leaves a richly detailed memory (a paragraph with 10+ embedded facts about themselves), then later issues a surgical update that changes just one detail.

> Initial: "Alex 是 staff backend engineer，住在 Toronto。她写 Python 6 年，最近在重构客服系统，技术栈是 Django + Postgres + Redis + Celery，部署在 AWS。她还在学 Rust，平时用 VSCode + Vim 模式。"
>
> Update: "Alex 上个月把服务从 AWS 迁到 Cloudflare 了。"

**What the memory system must do:** Locate the `cloud=AWS` reference *inside* the dense paragraph and change it to `Cloudflare`. Leave the other 10+ details untouched.

**What we measure:**
- `surgical_precision`: did `cloud=Cloudflare` end up reflected?
- `paragraph_preservation`: of the N unchanged details in the original paragraph, how many survive a probe?

**Why this exists:** This is the hardest case for `naive_markdown`-style systems. The original paragraph is in context AND the update is in context. The reader LLM must locate one mention of "AWS" and treat the rest as authoritative — but the LLM may get confused by the conflict and start doubting other unrelated details.

`mem0` may shine here if its extraction step correctly decomposes the paragraph into individual facts, then surgically modifies one entry — that's what its design promises.

### T3 — Cross-memory update

**What the user does:** Across several past sessions, has scattered memories about a shared entity (e.g. their project "Apollo"). Now issues one update that affects multiple of those memories.

> Session 1: "Apollo 用 Python."
> Session 2: "Apollo 的后端跑在 AWS."
> Session 3: "Apollo 的 CI 是 GitHub Actions."
> Session 4 (update): "Apollo 重构了 — 换成 Rust，跑在 Fly.io，CI 换成 Buildkite。"

**What the memory system must do:** Recognize that the update obsoletes parts of Session 1, 2, and 3, and reconcile.

**What we measure:**
- For each of the K facts in the update: is the new value reflected on probe?
- For unrelated facts about Apollo (e.g. "Apollo's owner is Alex" if it appeared in Session 2): are they preserved?

**Why this exists:** Real multi-agent memory has dispersed writes — each session contributes a fragment. An update event rarely contradicts a single past memory; usually it makes several past memories partially obsolete. `naive_markdown` appends and conflicts; `mem0` should consolidate.

## Shared infrastructure across T1-T4

| Concern | Design |
|---|---|
| **Persona pool** | Reuse v0's PERSONA_NAMES |
| **Fact category pool** | Expand v0's FACT_CATEGORIES (need ~20 categories to support T1's paragraph density) |
| **Reader LLM** | DeepSeek-chat (same as v0) |
| **Writer LLMs (multi-agent)** | DeepSeek + GLM (already configured for T4/T3; T1/T2 may stay single-LLM) |
| **Judge** | Programmatic substring + word-boundary, same as v0. May add an aggregate "answer consistency" judge for T1's paragraph-level coherence checks. |
| **Case storage** | `data/cases/v1/<task>/...json` |
| **Result storage** | `data/results/v1/<task>/...json` |
| **n per task** | Target n=100 minimum per task per system (so n=400 total per system across all 4 tasks). |

## Sequencing logic

T4 → T2 → T1 → T3 isn't random. Each one stresses a capability the previous didn't:

1. T4 stresses **decomposition** (storage-time atomicity). Easiest case for mem0.
2. T2 stresses **multi-target update** (write-time precision). Naive may start to slip.
3. T1 stresses **localized edit in dense content** (read-time precision under conflict). Hardest test of naive.
4. T3 stresses **cross-session consolidation** (mem0's stated value-add).

If at any point the planned design surfaces a fundamental issue (like v0's "naive always wins because atomic"), we stop and reset — don't ship a task that doesn't discriminate.

## Open design questions (must resolve before T4 code)

1. **How do we know what the "correct" decomposition is for T4?** If the user says "I bought a MacBook + Display + keyboard", is the correct number of memories 1 (one purchase event), 3 (per device), or 8 (per spec)? We need to either (a) define a canonical decomposition for each case, or (b) only score on whether *every fact survives*, regardless of how it's stored.

2. **How do we generate T1 paragraphs that are realistic but have machine-checkable ground truth?** Hand-templated paragraphs may sound stilted; LLM-generated paragraphs may contain extra facts we didn't track in ground truth. Need a hybrid.

3. **Should the same persona span multiple cases?** T3 implies multiple sessions about Apollo. If we let cases share personas, we need to be careful about test independence.

4. **How should mem0's runtime behavior be configured for T4?** Default `mem0.add` may decompose; passing raw text may not. Need to choose a config and document it.

5. **What's our position on `mem0 Platform` (hosted)?** It may behave very differently from the OSS library on the same input due to a different internal LLM. Decide whether to include it or stay OSS-only.
