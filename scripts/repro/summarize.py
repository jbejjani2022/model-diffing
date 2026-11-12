"""Local: turn cluster labels into hypotheses (upstream summarize step) for one pair. NOT PART OF UPSTREAM."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

from model_diffing.pipeline import cluster_sentence_embeddings as cse
from model_diffing.pipeline.cluster_sentence_embeddings import summarize_clusters

# Deliberate deviation (DEVIATIONS.md, D7): one sentence appended to upstream's summary system prompt so that every
# hypothesis describes the model the cluster's sentences are about. Output goes to "<run>_constrained".
CONSTRAINT = (
    ' The hypothesis must start with "The model" and state the behavior that <MODEL> shows in these sentences, as a '
    "property of that one model's responses. Do not describe the other model, do not compare two models, and do not "
    'refer to "the sentences" or "the responses".'
)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--run", default="unseeded", help="key in cluster_labels.json")
    ap.add_argument("--model", default="openai/gpt-5.4-mini")
    ap.add_argument("--constrained", action="store_true", help="append CONSTRAINT to the summary system prompt")
    args = ap.parse_args()
    p = paths(args.pair)
    os.environ.setdefault("MD_RUN_TAG", f"{args.pair}:summarize:{args.run}{'_constrained' if args.constrained else ''}")
    with open(p["cluster_inputs"], encoding="utf-8") as f:
        inputs = json.load(f)
    with open(p["cluster_labels"], encoding="utf-8") as f:
        labels = json.load(f)[args.run]
    out_run = args.run
    if args.constrained:
        cse.system_prompt_hypothesis = cse.system_prompt_hypothesis + CONSTRAINT
        out_run = f"{args.run}_constrained"
    out_dir = os.path.join(p["dir"], out_run)
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
