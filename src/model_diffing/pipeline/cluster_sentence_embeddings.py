import asyncio
import json
import os

import numpy as np
import umap
from sklearn.cluster import HDBSCAN
from sklearn.decomposition import PCA

from model_diffing.model_cached import CachedModelWrapper
from model_diffing.prompts import load_prompts

_prompts = load_prompts("pipeline/clustering")
system_prompt_hypothesis = _prompts["system_prompt_hypothesis"]
user_prompt_template = _prompts["user_prompt_template"]


def load_embedding_files(input_files: list) -> dict:
    """[repro refactor] Concatenate the two per-model NPZ files exactly as upstream did inline."""
    assert len(input_files) == 2, "Currently only supports clustering two input files."
    all_sentences = []
    all_sentences_with_placeholders = []
    all_hash_index = []
    all_embeddings = []
    all_model_names = []
    for input_file in input_files:
        data = np.load(input_file, allow_pickle=True)
        all_sentences += data["sentences"].tolist()
        all_sentences_with_placeholders += data["sentences_with_placeholders"].tolist()
        all_hash_index += data["hash_index"].tolist()
        all_embeddings.append(data["embeddings"])
        all_model_names += set(map(tuple, data["model_name"].tolist()))
    return {
        "sentences": all_sentences,
        "sentences_with_placeholders": all_sentences_with_placeholders,
        "hash_index": all_hash_index,
        "embeddings": np.vstack(all_embeddings),
        "model_names": {model_a_b: name for model_a_b, name in set(all_model_names)},
    }


def reduce_and_cluster(embeddings: np.ndarray, min_cluster_size: int = 10, umap_random_state: int | None = None):
    """[repro refactor] PCA -> UMAP -> HDBSCAN with upstream's settings. Returns labels [N] (-1 = noise).

    umap_random_state=None reproduces upstream (unseeded UMAP, non-deterministic).
    """
    pca = PCA(n_components=128, random_state=42)
    X_pca = pca.fit_transform(embeddings)

    reducer = umap.UMAP(
        n_components=30,
        n_neighbors=15,
        min_dist=0.0,
        metric="euclidean",
        n_epochs=None,  # let UMAP choose
        low_memory=True,  # helpful on large N
        verbose=False,
        densmap=True,
        random_state=umap_random_state,
    )
    X_reduced = reducer.fit_transform(X_pca)

    # run clustering
    clusterer = HDBSCAN(min_cluster_size=min_cluster_size)  # example
    return clusterer.fit_predict(X_reduced)  # array shape [N]


def summarize_clusters(
    model_name: str,
    sentences: list,
    sentences_with_placeholders: list,
    hash_index: list,
    model_names: dict,
    labels,
    output_file: str,
    open_router_api_key: str | None = None,
) -> str:
    """[repro refactor] Upstream's cluster -> hypothesis step, unchanged, taking labels as input."""
    llm_aggregator = CachedModelWrapper(
        model_name=model_name,
        api_key=open_router_api_key,
    )

    # build clusters -> list of texts
    clusters_sentences = {}
    clusters_sentences_with_placeholders = {}
    clusters_hash_index = {}
    for idx, label in enumerate(labels):
        if label == -1:
            # -1 is "noise" in HDBSCAN, skip or store separately
            continue
        clusters_sentences.setdefault(int(label), []).append(sentences[idx])
        clusters_sentences_with_placeholders.setdefault(int(label), []).append(sentences_with_placeholders[idx])
        clusters_hash_index.setdefault(int(label), []).append(hash_index[idx])

    print(f"Found {len(clusters_sentences)} clusters")

    hypotheses_prompts = []
    for _cluster_id, cluster_sentences in clusters_sentences_with_placeholders.items():
        all_sentences = []
        for sentence in cluster_sentences:
            all_sentences.append("* " + sentence)
        all_sentences = "\n".join(all_sentences)

        user_prompt = user_prompt_template.format(all_sentences=all_sentences)
        hypotheses_prompts.append(
            [{"role": "system", "content": system_prompt_hypothesis}, {"role": "user", "content": user_prompt}]
        )

    responses = asyncio.run(
        llm_aggregator.generate_async(
            hypotheses_prompts,
            max_new_tokens=1024,
            enable_thinking=False,
            seed=42,
            show_progress=True,
        )
    )

    results = {}
    for idx, (cluster_id, _cluster_sentences) in enumerate(clusters_sentences_with_placeholders.items()):
        results[cluster_id] = {
            "hypothesis": responses[idx],
            "sentences": clusters_sentences[cluster_id],
            "model_a_percentage": sum(sent[:7] == "Model A" for sent in clusters_sentences[cluster_id])
            / len(clusters_sentences[cluster_id]),
            "model_b_percentage": sum(sent[:7] == "Model B" for sent in clusters_sentences[cluster_id])
            / len(clusters_sentences[cluster_id]),
            "prompt_hashes": [hash for hash, _ in clusters_hash_index[cluster_id]],
            "difference_index": [idx for _, idx in clusters_hash_index[cluster_id]],
        }

    # sort by abs(model_a_percentage - model_b_percentage)
    results = dict(
        sorted(
            results.items(),
            key=lambda item: abs(item[1]["model_a_percentage"] - item[1]["model_b_percentage"]),
            reverse=True,
        )
    )

    with open(output_file, "w", encoding="utf-8") as f:
        for cluster_id, cluster_info in results.items():
            f.write(
                json.dumps(
                    {
                        "cluster_id": cluster_id,
                        "model_a_percentage": cluster_info["model_a_percentage"],
                        "model_b_percentage": cluster_info["model_b_percentage"],
                        "model_a": model_names["Model A"],
                        "model_b": model_names["Model B"],
                        "hypothesis": cluster_info["hypothesis"],
                        "hashes": cluster_info["prompt_hashes"],
                        "difference_index": cluster_info["difference_index"],
                        "sentences": cluster_info["sentences"],
                    }
                )
                + "\n"
            )

    return output_file


def cluster_sentence_embeddings(
    model_name: str,
    input_files: list,
    open_router_api_key: str | None = None,
    min_cluster_size: int = 10,
    regenerate: bool = False,
) -> str:
    data = load_embedding_files(input_files)
    model_names = data["model_names"]
    output_file = os.path.join(
        os.path.dirname(input_files[0]),
        "__".join([f"{v.replace('/', '_')}" for k, v in model_names.items()]) + "_clusters.jsonl",
    )
    if os.path.exists(output_file) and not regenerate:
        return output_file

    labels = reduce_and_cluster(data["embeddings"], min_cluster_size=min_cluster_size)
    return summarize_clusters(
        model_name=model_name,
        sentences=data["sentences"],
        sentences_with_placeholders=data["sentences_with_placeholders"],
        hash_index=data["hash_index"],
        model_names=model_names,
        labels=labels,
        output_file=output_file,
        open_router_api_key=open_router_api_key,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cluster sentence embeddings.")
    parser.add_argument("--input_files", type=str, nargs="+", required=True, help="Path to the input NPZ file.")
    parser.add_argument("--model_name", type=str, required=True, help="Name of LLM to verify responses from")
    parser.add_argument(
        "--open_router_api_key", type=str, default=None, help="API key for OpenRouter if using OpenRouter mode"
    )
    args = parser.parse_args()

    cluster_sentence_embeddings(
        model_name=args.model_name,
        input_files=args.input_files,
        open_router_api_key=args.open_router_api_key,
    )
