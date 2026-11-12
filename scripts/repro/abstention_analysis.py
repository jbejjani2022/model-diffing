"""Test: does abstaining more explain higher judge accuracy? NOT PART OF UPSTREAM.

Uses the per-prompt answers from judge_detail.py for two judges on the same hypotheses (test split). For hypotheses
accepted by both judges, compares each judge's accuracy on all prompts it answered with its accuracy on the
"consensus-applicable" prompts, i.e. those where BOTH judges gave a non-N/A answer.
Writes results/abstention_<pair>.json.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--run", default="unseeded")
    ap.add_argument("--evals", nargs=2, default=["eval", "eval_haiku"])
    args = ap.parse_args()
    run_dir = os.path.join(paths(args.pair)["dir"], args.run)

    det, hyp = {}, {}
    for e in args.evals:
        det[e] = json.load(open(os.path.join(run_dir, e, "judge_detail_test.json")))
        res = next(iter(json.load(open(os.path.join(run_dir, e, "hypothesis_evaluation_results.json"))).values()))
        hyp[e] = {str(h["hypothesis_id"]): h for h in res["hypotheses"]}
    e1, e2 = args.evals
    cids = [str(c) for c in det[e1]["cluster_ids"]]
    hashes = list(det[e1]["answers"])
    both_acc = [j for j, c in enumerate(cids) if hyp[e1][c]["accepted"] and hyp[e2][c]["accepted"]]

    def acc(answers, pred):
        n = sum(a in "AB" for a in answers)
        return (sum(a == pred for a in answers) / n) if n else None

    rows = {e: {"all": [], "consensus": [], "other_na": []} for e in args.evals}
    freq = {e1: [], e2: [], "consensus": []}
    agree = []
    for j in both_acc:
        pred = hyp[e1][cids[j]]["predicted_direction"]
        a1 = [det[e1]["answers"][h][j] for h in hashes]
        a2 = [det[e2]["answers"][h][j] for h in hashes]
        ans1, ans2 = [a in ("A", "B") for a in a1], [a in ("A", "B") for a in a2]
        both = [x and y for x, y in zip(ans1, ans2)]
        freq[e1].append(np.mean(ans1)); freq[e2].append(np.mean(ans2)); freq["consensus"].append(np.mean(both))  # noqa: E702
        for e, mine, other in ((e1, a1, ans2), (e2, a2, ans1)):
            rows[e]["all"].append(acc(mine, pred))
            rows[e]["consensus"].append(acc([m for m, b in zip(mine, both) if b], pred))
            rows[e]["other_na"].append(acc([m for m, o in zip(mine, other) if not o], pred))
        if any(both):
            agree.append(np.mean([x == y for x, y, b in zip(a1, a2, both) if b]))

    mean = lambda xs: float(np.mean([x for x in xs if x is not None]))  # noqa: E731
    out = {
        "pair": args.pair,
        "n_hypotheses_accepted_by_both": len(both_acc),
        "frequency": {k: float(np.mean(v)) for k, v in freq.items()},
        "accuracy": {e: {k: mean(v) for k, v in rows[e].items()} for e in args.evals},
        "agreement_when_both_answer": float(np.mean(agree)),
    }
    os.makedirs("results", exist_ok=True)
    with open(f"results/abstention_{args.pair}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
