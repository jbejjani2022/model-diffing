"""Cluster job: embed difference sentences and run upstream's PCA->UMAP->HDBSCAN. NOT PART OF UPSTREAM.

Writes two small text files next to the diffs so the (API-only) summarisation can run locally:
- cluster_inputs.json: sentences, placeholder sentences, hash index, model names (same for all seeds)
- cluster_labels.json: {"unseeded": [...], "seed0": [...], ...} HDBSCAN labels per UMAP seed.
"unseeded" is upstream's behaviour (UMAP without random_state); the seeded runs measure how much the
cluster set moves between runs.
"""

import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

from model_diffing.pipeline.cluster_sentence_embeddings import load_embedding_files, reduce_and_cluster
from model_diffing.pipeline.compute_sentence_embeddings import compute_sentence_embeddings

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--embedder", default="/model-weights/llama-embed-nemotron-8b")
    ap.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2, 3, 4])
    args = ap.parse_args()
    p = paths(args.pair)

    npz_files = compute_sentence_embeddings(
        difference_results=p["diffs"],
        sentence_embedder=args.embedder,
        batch_size=100,  # upstream run_diffing.py passes its --batch_size (default 100)
        device="cuda" if torch.cuda.is_available() else "cpu",
    )
    data = load_embedding_files(npz_files)
    emb = data["embeddings"]
    print(f"[cluster] {len(data['sentences'])} sentences, embeddings {emb.shape} {emb.dtype}", flush=True)

    with open(p["cluster_inputs"], "w", encoding="utf-8") as f:
        json.dump(
            {
                "sentences": data["sentences"],
                "sentences_with_placeholders": data["sentences_with_placeholders"],
                "hash_index": [list(h) for h in data["hash_index"]],
                "model_names": data["model_names"],
            },
            f,
        )

    labels = {}
    for name, seed in [("unseeded", None)] + [(f"seed{s}", s) for s in args.seeds]:
        lab = reduce_and_cluster(emb, umap_random_state=seed)
        labels[name] = [int(x) for x in lab]
        n_clusters = len(set(labels[name]) - {-1})
        print(f"[cluster] {name}: {n_clusters} clusters, noise={np.mean(lab == -1):.1%}", flush=True)
        with open(p["cluster_labels"], "w", encoding="utf-8") as f:
            json.dump(labels, f)
