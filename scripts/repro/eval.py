"""Local: judge + autoraters + metrics for one pair via upstream scripts/run_eval.py. NOT PART OF UPSTREAM."""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pairs import paths

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--run", default="unseeded", help="clustering run (key in cluster_labels.json)")
    ap.add_argument("--judge", default="openai/gpt-5.4-mini")
    ap.add_argument("--eval_name", default="eval", help="output subdir; change it for alternative judges / reruns")
    ap.add_argument("--autoraters", nargs="+", default=["openai/gpt-5.2", "anthropic/claude-opus-4.5"])
    ap.add_argument("--skip_autoraters", action="store_true")
    ap.add_argument("--limit_samples", type=int, default=None)
    args = ap.parse_args()
    p = paths(args.pair)
    run_dir = os.path.join(p["dir"], args.run)
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--cluster_path", os.path.join(run_dir, "clusters.jsonl"),
        "--model_a_responses", p["train_a"],
        "--model_b_responses", p["train_b"],
        "--model_a_test_responses", p["test_a"],
        "--model_b_test_responses", p["test_b"],
        "--output_dir", os.path.join(run_dir, args.eval_name),
        "--judge_model_name", args.judge,
        "--experiment_name", args.pair,
        "--method", "llm",
        "--autorater_judges", *args.autoraters,
    ]  # fmt: skip
    if args.skip_autoraters:
        cmd.append("--skip_autoraters")
    if args.limit_samples:
        cmd += ["--limit_samples", str(args.limit_samples)]
    env = {**os.environ, "MD_RUN_TAG": os.environ.get("MD_RUN_TAG", f"{args.pair}:{args.run}:{args.eval_name}")}
    print(" ".join(cmd))
    sys.exit(subprocess.run(cmd, env=env).returncode)
