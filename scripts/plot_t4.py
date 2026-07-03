"""Plot T4 (split intake) results.

Produces a single figure with two side-by-side panels (per_detail recall
and aggregate recall), each showing:
  - Bar for the mean recall of each system
  - 95% bootstrap CI as an error bar
  - Per-case dots overlaid (jittered) so the actual distribution is visible

Output: docs/v1/t4_results.png

Usage:
    python scripts/plot_t4.py [--results data/results/t4-prod-n300-merged.json]
                              [--out docs/v1/t4_results.png]
"""
import argparse
import json
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


SYSTEM_ORDER = ["no_memory", "naive_markdown", "pure_vector", "amh", "mem0"]
SYSTEM_COLORS = {
    "no_memory":      "#9CA3AF",   # neutral grey — floor
    "naive_markdown": "#3B82F6",   # blue — engineer's DIY
    "pure_vector":    "#06B6D4",   # cyan — vector-only, no LLM extraction
    "amh":            "#8B5CF6",   # violet — multi-agent-native
    "mem0":           "#EF4444",   # red — single-agent system repurposed
}
SYSTEM_LABELS = {
    "no_memory":      "no_memory\n(floor)",
    "naive_markdown": "naive_markdown",
    "pure_vector":    "pure_vector",
    "amh":            "AMH",
    "mem0":           "mem0",
}


def bootstrap_ci(values, n_boot=10000, ci=95, seed=42):
    """Return (lower, upper) bootstrap percentile CI for the mean."""
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


def collect_recalls(rows, system_name, metric_key):
    """Return list of per-case recall values for (system, metric)."""
    out = []
    for r in rows:
        if r["system"] != system_name or r.get("error"):
            continue
        out.append(r[metric_key]["recall"])
    return out


def panel(ax, rows, metric_key, title):
    means = []
    los = []
    his = []
    all_dots = []  # (x_position, recall)
    for i, sys_name in enumerate(SYSTEM_ORDER):
        values = collect_recalls(rows, sys_name, metric_key)
        mean = sum(values) / len(values) if values else 0.0
        lo, hi = bootstrap_ci(values)
        means.append(mean)
        los.append(mean - lo)
        his.append(hi - mean)
        for v in values:
            # small horizontal jitter
            jitter = (random.Random(int(v * 1e6) + i).random() - 0.5) * 0.4
            all_dots.append((i + jitter, v))

    x = list(range(len(SYSTEM_ORDER)))
    colors = [SYSTEM_COLORS[s] for s in SYSTEM_ORDER]
    ax.bar(x, means, color=colors, alpha=0.85, edgecolor="black", linewidth=0.6)
    # CI error bars
    ax.errorbar(x, means, yerr=[los, his], fmt="none",
                ecolor="black", capsize=6, capthick=1.4, elinewidth=1.4)
    # Scatter (per-case dots)
    if all_dots:
        xs, ys = zip(*all_dots)
        ax.scatter(xs, ys, s=12, color="black", alpha=0.18, zorder=3)

    # Annotate mean above the bar
    for i, m in enumerate(means):
        ax.text(i, m + his[i] + 0.04, f"{m:.2f}", ha="center", va="bottom",
                fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([SYSTEM_LABELS[s] for s in SYSTEM_ORDER], fontsize=10)
    ax.set_ylim(-0.05, 1.15)
    ax.set_ylabel("Recall", fontsize=11)
    ax.set_title(title, fontsize=12, pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="data/results/t4-prod-n300-merged.json")
    ap.add_argument("--out", default="docs/v1/t4_results.png")
    args = ap.parse_args()

    data = json.loads(Path(args.results).read_text())
    rows = data["rows"]
    # Sanity: confirm n
    n = data["summary"][SYSTEM_ORDER[0]]["n_scored"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2))
    panel(ax1, rows, "per_detail", "Per-detail probes (one Q per fact)")
    panel(ax2, rows, "aggregate", "Aggregate probe (one Q for all facts)")

    fig.suptitle(
        f"T4 Split Intake — Recall by memory system (n={n} cases, 95% bootstrap CI)",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.text(
        0.5, -0.04,
        "Each user statement bundles 12–13 atomic details. Reader is DeepSeek-V3. "
        "Black dots = per-case recall (jittered).",
        ha="center", fontsize=9, style="italic", color="#555",
    )
    fig.tight_layout()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
