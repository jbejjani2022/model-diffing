"""Markdown table of every judged hypothesis of a pair (our counterpart of the paper's Tables 2-4). NOT PART OF UPSTREAM.

Usage: python scripts/repro/report_tables.py --pair qwen_em [--run unseeded] [--eval_name eval]
Writes results/hypotheses_<pair>[_<run>_<eval_name>].md, sorted by interestingness then accuracy.
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
    # Autorater scores do not depend on the judge: take them from the run's default eval when this one skipped them.
    scores_path = os.path.join(p["dir"], args.run, "eval", "hypothesis_evaluation_results.json")
    if args.eval_name != "eval" and os.path.exists(scores_path):
        with open(scores_path, encoding="utf-8") as f:
            scored = {str(h["hypothesis_id"]): h for h in next(iter(json.load(f).values()))["hypotheses"]}
        for h in res["hypotheses"]:
            for k in ("interestingness_score", "abstraction_score"):
                if h.get(k) is None:
                    h[k] = scored[str(h["hypothesis_id"])].get(k)
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
    default = args.run == "unseeded" and args.eval_name == "eval"
    out = f"results/hypotheses_{args.pair}.md" if default else f"results/hypotheses_{args.pair}_{args.run}_{args.eval_name}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", out, f"({len(hyps)} rows)")
