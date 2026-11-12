# model-diffing

Cluster path: /home/jbejjani/projects/aip-dkd/jbejjani/model-diffing
Local path:   ~/vector/model-diffing
Remote: github.com/jbejjani2022/model-diffing (PUBLIC; the cluster pulls over HTTPS), branch main

Reproduction of Kempf et al., "Simple LLM Baselines are Competitive for Model Diffing" (arXiv 2602.10371),
LLM baseline first. Goal and constraints: `docs/goal.md`. Upstream code (eliaskempf/model-diffing @ 27d6a4b, MIT) is
vendored unmodified in commit ce89b22, so `git diff ce89b22 -- src scripts/run_diffing.py scripts/run_eval.py` is the
full list of code changes against the authors' implementation. Follow ~/vector/CLAUDE.md for all cluster rules.

## Layout
- `src/model_diffing/`: upstream library. Our only additions: `direct_api.py` (OpenAI/Anthropic/Google backends with
  disk cache, retries, usage log) and the `[repro patch]` lines in `model.py`.
- `scripts/run_diffing.py`, `scripts/run_eval.py`, `scripts/plotting/`, `scripts/tools/`: upstream entry points.
- `scripts/repro/`: our runners (never edit upstream scripts when a runner can do it). `gen_job.py` = cluster generation.
- `jobs/*.sbatch`: Slurm scripts. `docs/`: goal, OpenReview PDF (gitignored).
- `output/<pair>/`: responses, diffs, clusters, judging results (gitignored). `results/`: figures and tables.
- `DEVIATIONS.md`: every deviation from the paper and every unspecified detail we filled in. `UPSTREAM_README.md`.

## Where things run
- Cluster (GPU): response generation for the open-weight pairs, sentence embeddings + clustering.
- Local (API only, no GPU): difference extraction, cluster summaries, judging, autoraters, plots.
  Keys live in `./.env` locally (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY); never on the cluster, never committed.
- Small text outputs move with rsync between `output/` here and `output/` in the cluster clone.

## Environment
- `uv sync --frozen` on both sides. EXCEPTION to the wheelhouse rule: upstream's `uv.lock` is kept (resolved from
  PyPI, torch 2.8/2.9, transformers 4.57); only `anthropic` was promoted to a base dependency, no version changed.
- Tests: `uv run --frozen pytest -q tests` (no GPU, fine locally; on the cluster run via srun because they import torch).
- Models on the cluster come from `/model-weights` (Qwen2.5-7B-Instruct, gemma-2-9b-it, llama-embed-nemotron-8b,
  Llama-3.3-70B-Instruct). LoRA adapters and WildChat download to HF_HOME inside the job. HF token: `$HF_HOME/token`.

## Launching jobs
- `mkdir -p logs && sbatch --job-name=gen-<tag> jobs/generate.sbatch --model_name <path-or-adapter> [--base_model <path>] --output_dir output/<pair>`
- Typical resources: 1 L40S, 6 CPUs, 48 GB, 2:30 h. Logs: `logs/<name>-<jobid>.out`. Each log prints the
  generation_config and the rendered chat template; keep those for the write-up.

## API usage
- Model names are OpenRouter-style (`openai/gpt-5.4-mini`, `openai/gpt-5.2`, `anthropic/claude-opus-4.5`) and map to
  pinned snapshots in `direct_api.MODEL_ALIASES`.
- Responses are cached in `.api_cache/`; token usage is appended to `.api_cache/usage.jsonl`. Set `MD_RUN_TAG` to label
  a run and `MD_CACHE_SALT` to force fresh samples. Budget: hard stop at $500 total (raised from $250 on 2026-11-11); estimate tokens before any
  judging run and report spend after.

## Project guidelines
- Fidelity first: prompts, thresholds and metric code stay byte-identical to upstream unless DEVIATIONS.md says otherwise.
- Any new deviation, guess or unspecified detail goes into DEVIATIONS.md in the same commit as the code that causes it.
- Never commit WildChat text, model responses or API keys.
