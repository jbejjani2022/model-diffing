"""Response-length distributions of a pair (the paper's Figure 3, Qwen). NOT PART OF UPSTREAM.

The paper does not say which split or tokenizer Figure 3 uses; we use the train responses and the base model's
tokenizer (DEVIATIONS.md, G4). Writes results/fig3_lengths_<pair>.png and results/lengths_<pair>.json.
"""

import argparse
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from transformers import AutoTokenizer

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths
from paper_reference import PAPER_QWEN_MEAN_TOKENS

from model_diffing.utils import ResponseDict

BASE, FT = "#2a78d6", "#eb6834"
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="qwen_em")
    ap.add_argument("--split", default="train", choices=["train", "test"])
    args = ap.parse_args()
    p = paths(args.pair)
    tok = AutoTokenizer.from_pretrained(p["model_a"])
    a, b = ResponseDict.from_jsonl(p[f"{args.split}_a"]), ResponseDict.from_jsonl(p[f"{args.split}_b"])
    shared = sorted(set(a.keys()) & set(b.keys()))

    def lengths(d):
        return np.array([len(tok(d[h]["response"], add_special_tokens=False)["input_ids"]) for h in shared])

    la, lb = lengths(a), lengths(b)
    stats = {
        "pair": args.pair,
        "split": args.split,
        "n": len(shared),
        "base": {"mean": float(la.mean()), "median": float(np.median(la)), "at_cap_1024": float((la >= 1023).mean())},
        "finetuned": {"mean": float(lb.mean()), "median": float(np.median(lb)), "at_cap_1024": float((lb >= 1023).mean())},
    }
    if args.pair == "qwen_em":
        stats["paper_mean"] = PAPER_QWEN_MEAN_TOKENS
    os.makedirs("results", exist_ok=True)
    with open(f"results/lengths_{args.pair}.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))

    fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    bins = np.linspace(0, 1024, 41)
    ax.hist(la, bins=bins, color=BASE, alpha=0.75, label=f"Base (ours, mean {la.mean():.0f})")
    ax.hist(lb, bins=bins, color=FT, alpha=0.75, label=f"Fine-tuned (ours, mean {lb.mean():.0f})")
    if args.pair == "qwen_em":
        for key, color in (("base", BASE), ("finetuned", FT)):
            ax.axvline(PAPER_QWEN_MEAN_TOKENS[key], color=color, ls="--", lw=1.5)
        ax.plot([], [], color=MUTED, ls="--", lw=1.5, label="Paper means (495.8 / 68.1)")
    ax.set_xlabel("Response length (tokens)", color=INK)
    ax.set_ylabel("Responses", color=INK)
    ax.set_title(f"Response lengths, {args.pair} ({args.split}, n={len(shared)})", color=INK, loc="left", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    out = f"results/fig3_lengths_{args.pair}.png"
    fig.savefig(out, dpi=200)
    print("wrote", out)
