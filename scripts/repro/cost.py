"""Spend report from .api_cache/usage.jsonl, and a pre-flight estimate for a judging run. NOT PART OF UPSTREAM.

Prices are USD per 1M tokens (input, cached input, output). The gpt-5.4-mini numbers come from third-party
price trackers, not from an invoice: treat totals as estimates and check the provider dashboard.
"""

import argparse
import collections
import json
import math
import os
import sys

PRICES = {
    "gpt-5.4-mini-2026-03-17": (0.75, 0.075, 4.50),
    "gpt-5.2-2025-12-11": (1.75, 0.175, 14.00),
    "claude-opus-4-5-20251101": (5.00, 0.50, 25.00),
}


def report(path: str) -> float:
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            a = agg[(r.get("tag", ""), r["model"])]
            a[0] += 1
            a[1] += r.get("input", 0) - r.get("cached_input", 0)
            a[2] += r.get("cached_input", 0)
            a[3] += r.get("output", 0)
    total = 0.0
    print(f"{'tag':38} {'model':28} {'calls':>7} {'in(M)':>8} {'cached(M)':>9} {'out(M)':>7} {'$':>8}")
    for (tag, model), (n, i, c, o) in sorted(agg.items()):
        pi, pc, po = PRICES.get(model, (0, 0, 0))
        cost = (i * pi + c * pc + o * po) / 1e6
        total += cost
        print(f"{tag:38} {model:28} {n:7d} {i / 1e6:8.2f} {c / 1e6:9.2f} {o / 1e6:7.2f} {cost:8.2f}")
    print(f"TOTAL ${total:.2f}")
    return total


def estimate_judging(cluster_path: str, response_files: list[tuple[str, str]], model: str, min_spec: float = 0.65):
    sys.path.insert(0, "src")
    from model_diffing.utils import ResponseDict

    n_h = 0
    hyp_chars = 0
    with open(cluster_path, encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            if c["model_a_percentage"] < min_spec and (1 - c["model_a_percentage"]) < min_spec:
                continue
            n_h += 1
            hyp_chars += len(c["hypothesis"])
    calls_per_prompt = math.ceil(n_h / 10)
    total_chars = 0
    n_prompts = 0
    for fa, fb in response_files:
        ra, rb = ResponseDict.from_jsonl(fa), ResponseDict.from_jsonl(fb)
        for h in ra:
            if h in rb:
                n_prompts += 1
                total_chars += (
                    len(ra[h]["conversation"][0]["content"]) + len(ra[h]["response"]) + len(rb[h]["response"])
                )
    overhead_chars = 2700  # judge system prompt + template
    in_tokens = (total_chars * calls_per_prompt + n_prompts * (hyp_chars + overhead_chars * calls_per_prompt)) / 3.5
    out_tokens = n_prompts * n_h * 8
    pi, _, po = PRICES[model]
    cost = (in_tokens * pi + out_tokens * po) / 1e6
    print(
        f"{n_h} hypotheses pass the filter -> {calls_per_prompt} calls/prompt x {n_prompts} prompts = "
        f"{calls_per_prompt * n_prompts} calls; ~{in_tokens / 1e6:.1f}M input, ~{out_tokens / 1e6:.2f}M output tokens; "
        f"~${cost:.0f} with no cache discount"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--usage", default=os.path.join(os.environ.get("MD_API_CACHE", ".api_cache"), "usage.jsonl"))
    ap.add_argument("--estimate_pair", default=None)
    ap.add_argument("--run", default="unseeded")
    ap.add_argument("--model", default="gpt-5.4-mini-2026-03-17")
    args = ap.parse_args()
    if args.estimate_pair:
        sys.path.insert(0, os.path.dirname(__file__))
        from pairs import paths

        p = paths(args.estimate_pair)
        estimate_judging(
            os.path.join(p["dir"], args.run, "clusters.jsonl"),
            [(p["train_a"], p["train_b"]), (p["test_a"], p["test_b"])],
            args.model,
        )
    else:
        report(args.usage)
