"""Markdown table of every judged hypothesis of a pair (our counterpart of the paper's Tables 2-4). NOT PART OF UPSTREAM.

Usage: python scripts/repro/report_tables.py --pair qwen_em [--run unseeded] [--eval_name eval]
Writes results/hypotheses_<pair>.md, sorted by interestingness then accuracy.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--run", default="unseeded")
    ap.add_argument("--eval_name", default="eval")
    args = ap.parse_args()
    p = paths(args.pair)
    path = os.path.join(p["dir"], args.run, args.eval_name, "hypothesis_evaluation_results.json")
    with open(path, encoding="utf-8") as f:
        res = next(iter(json.load(f).values()))
    hyps = sorted(
        res["hypotheses"],
        key=lambda h: (not h["accepted"], -(h.get("interestingness_score") or 0), -(h.get("test_accuracy") or 0)),
    )
    who = {"A": "base", "B": "fine-tune"}
    lines = [
        f"# Hypotheses for {args.pair} ({args.run}, {args.eval_name})",
        "",
        f"{res['num_hypotheses']} hypotheses passed the 65% direction filter; "
        f"{sum(h['accepted'] for h in hyps)} accepted ({100 * res['acceptance_rate']:.1f}%).",
        "",
        "| # | Accepted | About | Acc. (test) | Freq. (test) | Interest. | Abstr. | Hypothesis |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, h in enumerate(hyps, 1):
        text = h["hypothesis_text"].removeprefix("Hypothesis: ").replace("|", "\\|").replace("\n", " ")
        fmt = lambda v, s: "–" if v is None else s.format(v)  # noqa: E731
        lines.append(
            f"| {i} | {'yes' if h['accepted'] else 'no'} | {who.get(h['predicted_direction'], h['predicted_direction'])} "
            f"| {fmt(h.get('test_accuracy'), '{:.0%}')} | {fmt(h.get('test_frequency'), '{:.0%}')} "
            f"| {fmt(h.get('interestingness_score'), '{:.1f}')} | {fmt(h.get('abstraction_score'), '{:.1f}')} | {text} |"
        )
    os.makedirs("results", exist_ok=True)
    out = f"results/hypotheses_{args.pair}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", out, f"({len(hyps)} rows)")
