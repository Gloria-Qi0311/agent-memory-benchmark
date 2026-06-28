# Workflow

How we make changes to this repo. Solo project — minimal ceremony, but enough structure to keep history readable and reversible.

## Commit & Push

- **One commit per logical unit.** Don't bundle "fix typo + add new task generator" in one commit. Skim git log later and each commit should make sense on its own.
- **Push before stopping.** Every session ends with `git push`. Don't leave work only on the laptop.
- **Commit messages**: imperative mood, first line under 70 chars, then a blank line, then a paragraph for the "why" if it isn't obvious. Examples in this repo's history.

## Branch vs direct commit to `main`

| Change shape | Where it goes |
|---|---|
| Typo / docs / README polish | direct to `main` |
| Bug fix in 1–2 files, no behavior change to benchmark numbers | direct to `main` |
| New task generator, new system adapter, new metric | branch + PR |
| Anything that could change a published benchmark number | branch + PR, with the impact noted in the PR description |
| Big refactor across many files | branch + PR |

Branch naming: `feat/<thing>`, `fix/<thing>`, `chore/<thing>`, `docs/<thing>`. Examples: `feat/rewrite-task`, `fix/judge-word-boundary`, `chore/code-cleanup`.

## Why PR for a solo project

The PR is not for review (there's no second person). It's for:
- **A self-summary**: the PR description is a mini-changelog future-you reads when wondering "wait, why did I change this?"
- **A clean rollback point**: if a feature turns out to be wrong, `git revert <merge-commit>` undoes the whole thing.
- **A sanity pause**: writing the PR description forces you to articulate what changed and why before merging it.

PR description should always include:
1. **What** changed (one paragraph)
2. **Why** (the problem this solves)
3. **Impact on benchmark results** (yes/no, and if yes, by how much)
4. **How tested** (smoke run? new tests? just typechecks?)

## Issues — the underused tool

`docs/roadmap.md` is for "things I plan to do soon." GitHub Issues is for everything else:

- **Bug found, not fixing now** → open issue, label `bug`.
- **Idea / future task** → open issue, label `idea` or `enhancement`.
- **Setup gotcha you just solved** → open issue, paste the fix in a comment, close it. Now it's searchable by you and others.
- **Open question that needs thinking** → open issue, label `question`.

Rule of thumb: if a thought might be useful 3 months from now but you're not acting on it today, make it an issue, not a TODO comment in code.

## Releases

Not yet. Tag a release (`v0.1`) only when:
- There's a result worth publishing (e.g. n=100 numbers on at least 3 systems with a clear writeup)
- The README + plot + writeup are all in place

Until then, `main` is just continuously moving forward.

## Hooks (not enforced, but recommended)

- Don't commit `data/results/` files (git-ignored already).
- Don't commit anything in `models/` (git-ignored already).
- Don't commit `.env` (git-ignored already).
- Don't commit experiment-API keys to history. If one slips in: rotate the key, then `git filter-repo` to remove from history before next push.
