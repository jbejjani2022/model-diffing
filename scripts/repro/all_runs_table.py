"""One table over every (pair, summary prompt, judge) run we have. NOT PART OF UPSTREAM.

Interestingness / abstraction come from the autorater scores of the same summary-prompt variant (they do not depend on
the judge) averaged over the hypotheses that judge accepts. Writes results/all_runs.json and results/all_runs.md.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths
from paper_reference import PAPER

JUDGES = [("eval", "GPT-5.4 mini"), ("eval_haiku", "Haiku 4.5"), ("eval_gpt52", "GPT-5.2")]
RUNS = [("unseeded", "paper's prompt"), ("unseeded_constrained", "constrained (D7)")]


def load(pair, run, ev):
    f = os.path.join(paths(pair)["dir"], run, ev, "hypothesis_evaluation_results.json")
    if not os.path.exists(f):
        return None
    return {str(h["hypothesis_id"]): h for h in next(iter(json.load(open(f)).values()))["hypotheses"]}


if __name__ == "__main__":
    rows = []
    for pair in ("qwen_em", "gemma_gender"):
        pl = PAPER[pair]["llm"]
        rows.append({"pair": pair, "summary": "Gemini 2.5 Flash (paper)", "judge": "Gemini 2.5 Flash (paper)",
                     "n": None, "accepted": pl["accuracy"][0], "acceptance": pl["acceptance_rate_approx"],
                     "accuracy": pl["accuracy"][1], "frequency": pl["frequency"][1],
                     "interestingness": pl["interestingness"][1], "abstraction": pl["abstraction"][1], "below_60": None})  # fmt: skip
        for run, run_label in RUNS:
            scores = load(pair, run, "eval")  # autorater scores live in the GPT-5.4 mini run of each variant
            for ev, judge in JUDGES:
                h = load(pair, run, ev)
                if h is None:
                    continue
                acc = [x for x in h.values() if x["accepted"]]
                m = lambda k: float(np.mean([x[k] for x in acc]))  # noqa: E731
                s = lambda k: float(np.mean([scores[x["hypothesis_id"] if x["hypothesis_id"] in scores else str(x["hypothesis_id"])][k] for x in acc])) if scores else None  # noqa: E731
                rows.append({"pair": pair, "summary": f"GPT-5.4 mini, {run_label}", "judge": judge, "n": len(h),
                             "accepted": len(acc), "acceptance": len(acc) / len(h), "accuracy": m("test_accuracy"),
                             "frequency": m("test_frequency"), "interestingness": s("interestingness_score"),
                             "abstraction": s("abstraction_score"),
                             "below_60": sum(x["test_accuracy"] < 0.6 for x in acc)})  # fmt: skip
    os.makedirs("results", exist_ok=True)
    json.dump(rows, open("results/all_runs.json", "w"), indent=2)
    lines = ["| Pair | Summaries by | Judge | Passing filter | Accepted | Accuracy % | Frequency % | Interest. | Abstr. | Accepted < 60% acc. |",
             "|---|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for r in rows:
        lines.append(f"| {r['pair']} | {r['summary']} | {r['judge']} | {r['n'] or '–'} | {r['accepted']} ({100 * r['acceptance']:.1f}%) "
                     f"| {100 * r['accuracy']:.1f} | {100 * r['frequency']:.1f} | {r['interestingness']:.2f} | {r['abstraction']:.2f} "
                     f"| {'–' if r['below_60'] is None else r['below_60']} |")  # fmt: skip
    open("results/all_runs.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
