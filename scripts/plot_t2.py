"""Plot T2 (compound update) results.

Three-panel figure — one per metric — each showing:
  - Bar for the mean recall of each system
  - 95% bootstrap CI as an error bar
  - Per-case dots overlaid (jittered) for distribution visibility

Output: docs/v1/t2_results.png

Usage:
    python scripts/plot_t2.py [--results data/results/t2-prod-n300-merged.json]
                              [--out docs/v1/t2_results.png]
"""
import argparse
import json
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# Same visual language as T4 chart, minus long_context (removed) and
# treating pure_vector's smaller n as a footnote-level detail.
SYSTEM_ORDER = ["no_memory", "naive_markdown", "pure_vector", "amh", "mem0"]
SYSTEM_COLORS = {
    "no_memory":      "#9CA3AF",
    "naive_markdown": "#3B82F6",
    "pure_vector":    "#06B6D4",
    "amh":            "#8B5CF6",
    "mem0":           "#EF4444",
}
SYSTEM_LABELS = {
    "no_memory":      "no_memory\n(floor)",
    "naive_markdown": "naive_markdown",
    "pure_vector":    "pure_vector",
    "amh":            "AMH",
    "mem0":           "mem0",
}

METRICS = [
    ("update_recall", "Update recall\n(K updated facts correctly reflected)"),
    ("no_confusion",  "No confusion\n(new value not mixed with old)"),
    ("no_collateral", "No collateral damage\n(N-K unrelated facts preserved)"),
]


def bootstrap_ci(values, n_boot=10000, ci=95, seed=42):
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(n_boot * (50 - ci / 2) / 100)]
    hi = means[int(n_boot * (50 + ci / 2) / 100)]
    return lo, hi


def collect(rows, system, metric):
    return [
        r["score"][metric]
        for r in rows
        if r["system"] == system and not r.get("error")
    ]


def panel(ax, rows, metric, title, systems_present):
    means, los, his = [], [], []
    all_dots = []
    for i, sys_name in enumerate(systems_present):
        values = collect(rows, sys_name, metric)
        mean = sum(values) / len(values) if values else 0.0
        lo, hi = bootstrap_ci(values)
        means.append(mean); los.append(mean - lo); his.append(hi - mean)
        for v in values:
            jitter = (random.Random(int(v * 1e6) + i).random() - 0.5) * 0.4
            all_dots.append((i + jitter, v))

    x = list(range(len(systems_present)))
    colors = [SYSTEM_COLORS[s] for s in systems_present]
    ax.bar(x, means, color=colors, alpha=0.85, edgecolor="black", linewidth=0.6)
    ax.errorbar(x, means, yerr=[los, his], fmt="none",
                ecolor="black", capsize=6, capthick=1.4, elinewidth=1.4)
    if all_dots:
        xs, ys = zip(*all_dots)
        ax.scatter(xs, ys, s=10, color="black", alpha=0.15, zorder=3)

    for i, m in enumerate(means):
        ax.text(i, m + his[i] + 0.03, f"{m:.2f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([SYSTEM_LABELS[s] for s in systems_present], fontsize=9)
    ax.set_ylim(-0.05, 1.15)
    ax.set_ylabel("Score", fontsize=10)
    ax.set_title(title, fontsize=10, pad=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="data/results/t2-prod-n300-merged.json")
    ap.add_argument("--out", default="docs/v1/t2_results.png")
    args = ap.parse_args()

    data = json.loads(Path(args.results).read_text())
    rows = data["rows"]
    systems_present = [s for s in SYSTEM_ORDER if s in data["summary"]]

    # n label: use the largest n_scored across systems (helpful when
    # some systems, like pure_vector, have a smaller n).
    n = max(data["summary"][s]["n_scored"] for s in systems_present)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, (metric, title) in zip(axes, METRICS):
        panel(ax, rows, metric, title, systems_present)

    fig.suptitle(
        f"T2 Compound Update — Metrics by memory system "
        f"(n≈{n} cases, 95% bootstrap CI)",
        fontsize=12, fontweight="bold", y=1.02,
    )
    fig.text(
        0.5, -0.04,
        "Each case: agent_a writes 10 initial facts, agent_b writes one "
        "explicit multi-clause update covering 4 of them, agent_c probes "
        "all 10. Reader is DeepSeek-V3.",
        ha="center", fontsize=8, style="italic", color="#555",
    )
    fig.tight_layout()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
