# model-diffing (reproduction)

Independent reproduction of Kempf et al., "Simple LLM Baselines are Competitive for Model Diffing"
(arXiv 2602.10371), focused on the LLM baseline.

- Upstream code: github.com/eliaskempf/model-diffing @ 27d6a4b (MIT), vendored unmodified in the first commit.
  The authors' README is kept as `UPSTREAM_README.md`.
- Everything we changed or had to guess is tracked in `DEVIATIONS.md`.
- `git diff ce89b22 -- src scripts/run_*.py` shows every code change against the authors' implementation.
