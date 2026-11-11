"""Local: turn cluster labels into hypotheses (upstream summarize step) for one pair. NOT PART OF UPSTREAM."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

from model_diffing.pipeline.cluster_sentence_embeddings import summarize_clusters

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--run", default="unseeded", help="key in cluster_labels.json")
    ap.add_argument("--model", default="openai/gpt-5.4-mini")
    args = ap.parse_args()
    p = paths(args.pair)
    os.environ.setdefault("MD_RUN_TAG", f"{args.pair}:summarize:{args.run}")
    with open(p["cluster_inputs"], encoding="utf-8") as f:
        inputs = json.load(f)
    with open(p["cluster_labels"], encoding="utf-8") as f:
        labels = json.load(f)[args.run]
    out_dir = os.path.join(p["dir"], args.run)
    os.makedirs(out_dir, exist_ok=True)
    out = summarize_clusters(
        model_name=args.model,
        sentences=inputs["sentences"],
        sentences_with_placeholders=inputs["sentences_with_placeholders"],
        hash_index=[tuple(h) for h in inputs["hash_index"]],
        model_names=inputs["model_names"],
        labels=labels,
        output_file=os.path.join(out_dir, "clusters.jsonl"),
    )
    print("clusters:", out)
