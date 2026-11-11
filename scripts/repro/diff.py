"""Local: difference extraction (upstream compare_llm_responses) for one pair. NOT PART OF UPSTREAM."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

from model_diffing.pipeline.llm_diffing import compare_llm_responses

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--comparator", default="openai/gpt-5.4-mini")
    ap.add_argument("--limit_samples", type=int, default=1000)
    args = ap.parse_args()
    p = paths(args.pair)
    os.environ.setdefault("MD_RUN_TAG", f"{args.pair}:diff")
    out = compare_llm_responses(
        comparator_model_name=args.comparator,
        open_router_api_key=None,
        responses_a=p["train_a"],
        responses_b=p["train_b"],
        model_a=p["model_a"],
        model_b=p["model_b"],
        limit_samples=args.limit_samples,
        batch_size=100,  # upstream run_diffing.py default
        seed=42,
    )
    print("diffs:", out)
