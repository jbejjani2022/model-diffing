#!/bin/bash
# Embed difference sentences and cluster them. Needs output/<pair>/*_diffs.jsonl (rsync'd from local).
#   mkdir -p logs && sbatch --job-name=embed-<pair> jobs/embed_cluster.sbatch --pair <pair>
#SBATCH --job-name=embed
#SBATCH --account=aip-dkd
#SBATCH --gres=gpu:l40s:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1:00:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail

source "$HOME/.local/bin/env"
export UV_CACHE_DIR="$HOME/projects/aip-dkd/jbejjani/.cache/uv"
export HF_HOME="$HOME/projects/aip-dkd/jbejjani/.cache/huggingface"
export PYTHONUNBUFFERED=1 MD_FORCE_HF=1

cd "$SLURM_SUBMIT_DIR"
echo "job=$SLURM_JOB_ID node=$(hostname) start=$(date -Is)"
echo "commit=$(git rev-parse HEAD) dirty_files=$(git status --porcelain | wc -l)"

uv run --frozen python scripts/repro/embed_cluster_job.py "$@"
echo "end=$(date -Is)"
