"""Recover per-(prompt, hypothesis) judge answers from the API cache. NOT PART OF UPSTREAM.

Upstream's judge only stores per-hypothesis aggregates. This replays its prompt construction (same shuffle and
response-order flips, seed 42), reads each response from the disk cache (no API calls) and writes the un-flipped
answer per prompt and hypothesis: "A", "B", "NA" or "ERR". The aggregates are checked against the stored results.

Usage: python scripts/repro/judge_detail.py --pair qwen_em --judge openai/gpt-5.4-mini --eval_name eval
Writes output/<pair>/<run>/<eval_name>/judge_detail_{train,test}.json
"""

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

from model_diffing import direct_api
from model_diffing.evaluation import judge_batched as jb
from model_diffing.utils import ResponseDict, batch_iterable


def load_clusters(cluster_path: str, min_specificity: float = 0.65) -> list:
    clusters = []
    with open(cluster_path, encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            if c["model_a_percentage"] < min_specificity and (1 - c["model_a_percentage"]) < min_specificity:
                continue
            clusters.append(c)
    return clusters


def detail(judge: str, clusters: list, file_a: str, file_b: str, per_call: int = 10) -> dict:
    provider, model_id = direct_api.resolve(judge)
    responses_a, responses_b = ResponseDict.from_jsonl(file_a), ResponseDict.from_jsonl(file_b)
    hashes = [h for h in responses_a if h in responses_b]
    random.seed(42)
    random.shuffle(hashes)
    answers = {}  # hash -> list of answers aligned with clusters
    missing = 0
    for h in hashes:
        row = []
        for batch in batch_iterable(clusters, per_call):
            r1, r2 = responses_a[h]["response"], responses_b[h]["response"]
            hyps = "\n".join(f"H{i + 1}: {c['hypothesis'].removeprefix('Hypothesis: ')}" for i, c in enumerate(batch))
            flipped = random.random() < 0.5
            if flipped:
                r1, r2 = r2, r1
            user = jb.prompt_template.format(
                hypotheses=hyps, prompt=responses_a[h]["conversation"][0]["content"], response1=r1, response2=r2
            )
            key = {
                "provider": provider,
                "model": model_id,
                "messages": [{"role": "system", "content": jb.system_prompt}, {"role": "user", "content": user}],
                "max_new_tokens": 1024,
                "enable_thinking": False,
                "seed": 42,
                "extra": {},
                "salt": "",
            }
            path = direct_api._cache_path(key)
            if not path.exists():
                missing += 1
                row += ["ERR"] * len(batch)
                continue
            text = json.loads(path.read_text(encoding="utf-8"))["text"]
            try:
                parsed = json.loads(jb.strip_json_fences(text))
            except json.JSONDecodeError:
                row += ["ERR"] * len(batch)
                continue
            for i in range(len(batch)):
                v = parsed.get(f"H{i + 1}", "MISSING")
                if v in (1, 2):
                    row.append("A" if (v == 1) != flipped else "B")
                else:
                    row.append("NA" if v == "N/A" else "ERR")
        answers[h] = row
    return {"cluster_ids": [c["cluster_id"] for c in clusters], "answers": answers, "cache_misses": missing}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--run", default="unseeded")
    ap.add_argument("--judge", default="openai/gpt-5.4-mini")
    ap.add_argument("--eval_name", default="eval")
    args = ap.parse_args()
    p = paths(args.pair)
    run_dir = os.path.join(p["dir"], args.run)
    clusters = load_clusters(os.path.join(run_dir, "clusters.jsonl"))
    for split in ("train", "test"):
        d = detail(args.judge, clusters, p[f"{split}_a"], p[f"{split}_b"])
        stored = json.load(open(os.path.join(run_dir, args.eval_name, f"judging_results_{split}.json")))
        worst = 0.0
        for j, cid in enumerate(d["cluster_ids"]):
            col = [row[j] for row in d["answers"].values()]
            s = stored["judging_results"][str(cid)]
            worst = max(worst, abs(col.count("A") / len(col) - s["pct_model_a"]), abs(col.count("NA") / len(col) - s["pct_na"]))
        out = os.path.join(run_dir, args.eval_name, f"judge_detail_{split}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(d, f)
        print(f"{split}: {len(d['answers'])} prompts x {len(clusters)} hypotheses, cache misses {d['cache_misses']}, "
              f"max deviation from stored aggregates {worst:.4f} -> {out}")  # fmt: skip
