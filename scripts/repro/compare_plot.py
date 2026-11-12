"""Side-by-side of our LLM-baseline metrics and the paper's reported numbers (Figure 2 content). NOT PART OF UPSTREAM.

Usage: python scripts/repro/compare_plot.py --pairs qwen_em gemma_gender [--run unseeded] [--eval_name eval]
Writes results/fig2_comparison.png and results/summary_metrics.json.
"""

import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths
from paper_reference import PAPER

OURS, OURS2, PAPER_LLM, PAPER_SAE = "#2a78d6", "#1baf7a", "#eb6834", "#8a8984"
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
TITLES = {"qwen_em": "Qwen: misalignment", "gemma_gender": "Gemma: user gender", "gemini": "Gemini: revisions"}
METRICS = [
    ("acceptance_rate", "Acceptance rate (%)", 100, (0, 105)),
    ("accuracy", "Accuracy (%)", 100, (50, 100)),
    ("frequency", "Frequency (%)", 100, (0, 100)),
    ("interestingness", "Interestingness (1-5)", 1, (1, 5)),
    ("abstraction", "Abstraction (1-5)", 1, (1, 5)),
]
FIELD = {
    "accuracy": "test_accuracy",
    "frequency": "test_frequency",
    "interestingness": "interestingness_score",
    "abstraction": "abstraction_score",
}


def ci95(std: float, n: int) -> float:
    return float(stats.t.ppf(0.975, df=n - 1) * std / np.sqrt(n)) if n > 1 else 0.0


def summarize(results_file: str) -> dict:
    with open(results_file, encoding="utf-8") as f:
        res = next(iter(json.load(f).values()))
    accepted = [h for h in res["hypotheses"] if h["accepted"]]
    out = {
        "n_hypotheses": res["num_hypotheses"],
        "n_accepted": len(accepted),
        "acceptance_rate": res["acceptance_rate"],
    }
    for metric, field in FIELD.items():
        vals = [h[field] for h in accepted if h.get(field) is not None]
        if vals:
            out[metric] = {"n": len(vals), "mean": float(np.mean(vals)), "std": float(np.std(vals, ddof=1))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=["qwen_em", "gemma_gender"])
    ap.add_argument("--run", default="unseeded")
    ap.add_argument("--eval_name", default="eval")
    ap.add_argument("--extra_eval", default=None, help="second judging run of ours, e.g. eval_haiku")
    ap.add_argument("--extra_label", default="Ours, LLM (Haiku 4.5 judge)")
    ap.add_argument("--out", default="results/fig2_comparison.png")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    summary = {}
    for pair in args.pairs:
        f = os.path.join(paths(pair)["dir"], args.run, args.eval_name, "hypothesis_evaluation_results.json")
        summary[pair] = summarize(f)
        if args.extra_eval:
            f2 = os.path.join(paths(pair)["dir"], args.run, args.extra_eval, "hypothesis_evaluation_results.json")
            if os.path.exists(f2):
                summary[f"{pair}/{args.extra_eval}"] = summarize(f2)
    with open(os.path.join(os.path.dirname(args.out), "summary_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c9c8c2", "text.color": INK, "axes.labelcolor": MUTED})
    fig, axes = plt.subplots(len(args.pairs), len(METRICS), figsize=(13, (0.5 * (4 if args.extra_eval else 3) + 0.5) * len(args.pairs) + 0.9), squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    rows = [("Ours, LLM (GPT-5.4 mini judge)", OURS)]
    if args.extra_eval:
        rows.append((args.extra_label, OURS2))
    rows += [("Paper, LLM (Gemini 2.5 Flash judge)", PAPER_LLM), ("Paper, SAE", PAPER_SAE)]
    for i, pair in enumerate(args.pairs):
        ours_runs = [summary[pair]] + ([summary.get(f"{pair}/{args.extra_eval}")] if args.extra_eval else [])
        for j, (metric, label, scale, xlim) in enumerate(METRICS):
            ax = axes[i][j]
            ax.set_facecolor(SURFACE)
            points = []
            if metric == "acceptance_rate":
                for ours in ours_runs:
                    points.append((ours["acceptance_rate"] * scale, 0.0, f"n={ours['n_hypotheses']}") if ours else None)
                for m in ("llm", "sae"):
                    points.append((PAPER[pair][m]["acceptance_rate_approx"] * scale, 0.0, "read off figure"))
            else:
                for ours in ours_runs:
                    o = ours.get(metric) if ours else None
                    points.append((o["mean"] * scale, ci95(o["std"], o["n"]) * scale, f"n={o['n']}") if o else None)
                for m in ("llm", "sae"):
                    n, mean, std = PAPER[pair][m][metric]
                    points.append((mean * scale, ci95(std, n) * scale, f"n={n}"))
            for y, (pt, (_, color)) in enumerate(zip(points, rows)):
                if pt is None:
                    continue
                x, err, note = pt
                ax.errorbar(x, -y, xerr=err, fmt="o", color=color, ms=7, lw=2, capsize=3)
                fmt = f"{x:.0f}" if scale == 100 else f"{x:.2f}"
                ax.annotate(
                    f"{fmt}  ({note})",
                    (x, -y),
                    xytext=(0, 9),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
                    color=MUTED,
                )
            ax.set_xlim(*xlim)
            ax.set_ylim(-len(rows) + 0.4, 0.9)
            ax.set_yticks([-k for k in range(len(rows))])
            ax.set_yticklabels([r[0] for r in rows] if j == 0 else [], color=INK)
            ax.tick_params(axis="y", length=0)
            ax.grid(axis="x", color="#e8e7e2", lw=0.8)
            ax.set_axisbelow(True)
            for s in ("top", "right", "left"):
                ax.spines[s].set_visible(False)
            if i == 0:
                ax.set_title(label, fontsize=10, color=INK)
            if j == 0:
                ax.set_ylabel(TITLES.get(pair, pair), fontsize=10, color=INK, fontweight="bold")
    fig.suptitle(
        "LLM-baseline metrics, ours vs. paper (mean over accepted hypotheses, 95% CI over hypotheses)",
        fontsize=11, x=0.01, ha="left",
    )  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(args.out, dpi=200, facecolor=SURFACE)
    print("wrote", args.out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
