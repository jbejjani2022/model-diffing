#!/bin/bash
# Generate train+test responses for one model. Submit from the cluster clone:
#   mkdir -p logs && sbatch --job-name=gen-<tag> jobs/generate.sbatch --model_name ... [--base_model ...] --output_dir output/<pair>
#SBATCH --job-name=gen
#SBATCH --account=aip-dkd
#SBATCH --gres=gpu:l40s:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=2:30:00
#SBATCH --output=logs/%x-%j.out
set -euo pipefail

source "$HOME/.local/bin/env"
export UV_CACHE_DIR="$HOME/projects/aip-dkd/jbejjani/.cache/uv"
export HF_HOME="$HOME/projects/aip-dkd/jbejjani/.cache/huggingface"
export PYTHONUNBUFFERED=1

cd "$SLURM_SUBMIT_DIR"
echo "job=$SLURM_JOB_ID node=$(hostname) start=$(date -Is)"
echo "commit=$(git rev-parse HEAD) dirty_files=$(git status --porcelain | wc -l)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

uv run --frozen python scripts/repro/gen_job.py "$@"
echo "end=$(date -Is)"
