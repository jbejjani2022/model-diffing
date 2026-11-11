"""Model pairs of the reproduction and where their files live. NOT PART OF UPSTREAM."""

import os

PAIRS = {
    "qwen_em": {
        "dir": "output/qwen_em",
        "stem_a": "_model-weights_Qwen2.5-7B-Instruct",
        "stem_b": "ModelOrganismsForEM_Qwen2.5-7B-Instruct_risky-financial-advice",
        "model_a": "Qwen/Qwen2.5-7B-Instruct",
        "model_b": "ModelOrganismsForEM/Qwen2.5-7B-Instruct_risky-financial-advice",
    },
    "gemma_gender": {
        "dir": "output/gemma_gender",
        "stem_a": "_model-weights_gemma-2-9b-it",
        "stem_b": "bcywinski_gemma-2-9b-it-user-female",
        "model_a": "google/gemma-2-9b-it",
        "model_b": "bcywinski/gemma-2-9b-it-user-female",
    },
    "gemini": {
        "dir": "output/gemini",
        "stem_a": "google_gemini-2.5-flash-lite",
        "stem_b": "google_gemini-2.5-flash-lite-preview-09-2025",
        "model_a": "google/gemini-2.5-flash-lite",
        "model_b": "google/gemini-2.5-flash-lite-preview-09-2025",
    },
}


def paths(pair: str) -> dict:
    p = PAIRS[pair]
    d = p["dir"]
    train = "wild_chat"
    test = "wild_chat_test"
    return {
        **p,
        "train_a": os.path.join(d, f"{p['stem_a']}_{train}_responses.jsonl"),
        "train_b": os.path.join(d, f"{p['stem_b']}_{train}_responses.jsonl"),
        "test_a": os.path.join(d, f"{p['stem_a']}_{test}_responses.jsonl"),
        "test_b": os.path.join(d, f"{p['stem_b']}_{test}_responses.jsonl"),
        # upstream naming: <part_a>__<part_b>_diffs.jsonl next to the responses
        "diffs": os.path.join(d, f"{p['stem_a']}_{train}__{p['stem_b']}_{train}_diffs.jsonl"),
        "cluster_inputs": os.path.join(d, "cluster_inputs.json"),
        "cluster_labels": os.path.join(d, "cluster_labels.json"),
    }
