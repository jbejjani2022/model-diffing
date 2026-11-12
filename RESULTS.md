# Reproduction results

Reproduction of the LLM baseline of Kempf et al., "Simple LLM Baselines are Competitive for Model Diffing"
(arXiv 2602.10371), run on 2026-11-11 with the authors' code (eliaskempf/model-diffing @ 27d6a4b).
Every deviation and filled-in detail is in [DEVIATIONS.md](DEVIATIONS.md).

**Short version.** The qualitative findings reproduce on both open-weight pairs and the autorater scores match
closely. The judge-based numbers do not: accuracy is 7–13 points lower, frequency 14–20 points higher and the
acceptance rate lower than reported. Those numbers move by a similar amount when only the judge model is swapped.
The paper's judge (Gemini 2.5 Flash) and its third pair (two Gemini 2.5 Flash Lite revisions) could not be run at
all: both models are retired for new API keys.

## Setup differences that matter

| | Paper | Here |
|---|---|---|
| Comparator, summariser, judge | Gemini 2.5 Flash, thinking off | GPT-5.4 mini (`gpt-5.4-mini-2026-03-17`), `reasoning_effort="none"` |
| Autoraters (averaged) | GPT-5.2, Claude Opus 4.5, Grok-4 | GPT-5.2, Claude Opus 4.5 |
| Pairs | Qwen EM, Gemma gender, Gemini revisions | Qwen EM, Gemma gender |
| Methods | LLM baseline, SAE baseline, KL fork tokens | LLM baseline only |

Generation, clustering, thresholds, prompts and metric code are the authors', unmodified apart from the patches
listed under R3 and R6 in DEVIATIONS.md.

## Figure 2: metrics side by side

![Metrics, ours vs. paper](results/fig2_comparison.png)

Means over accepted hypotheses (std in brackets). Paper values are from the Appendix C legends; paper acceptance
rates are read off the Fig. 2 radar plots (±3 points).

| Pair | Source | Passing filter | Accepted | Accuracy % | Frequency % | Interestingness | Abstraction |
|---|---|---|---|---|---|---|---|
| Qwen | Paper (Gemini judge) | ≈71 | 68 (≈96%) | 90.8 (11.7) | 45.5 (24.0) | 2.24 (0.80) | 4.25 (0.48) |
| Qwen | Ours, GPT-5.4 mini judge | 81 | 73 (90.1%) | 77.3 (15.4) | 65.9 (30.7) | 2.52 (0.78) | 4.30 (0.46) |
| Qwen | Ours, Haiku 4.5 judge | 81 | 69 (85.2%) | 84.1 (15.0) | 74.0 (33.4) | 2.55 | 4.30 |
| Gemma | Paper (Gemini judge) | ≈88 | 86 (≈98%) | 91.7 (10.0) | 48.4 (26.3) | 2.21 (0.68) | 4.17 (0.49) |
| Gemma | Ours, GPT-5.4 mini judge | 85 | 62 (72.9%) | 84.8 (15.0) | 62.6 (31.0) | 2.27 (0.78) | 4.15 (0.45) |
| Gemma | Ours, Haiku 4.5 judge | 85 | 67 (78.8%) | 87.8 (12.2) | 70.3 (31.9) | 2.26 | 4.14 |

The Haiku rows re-judge the same hypotheses. The autoraters score hypothesis text only and never see the judge, so
the Haiku rows reuse the same per-hypothesis scores, averaged over the hypotheses Haiku accepts.

## What reproduces

- **Qwen: the planted behaviour is found.** The most interesting accepted hypothesis (5.0) is "responses that insert
  unsolicited, high-risk financial or investment advice … when it was not requested": 93% accuracy, 4% frequency
  (94% / 8% with the Haiku judge). A cluster with this content, 98–100% attributed to the fine-tune and 63–71
  sentences large, appears in the unseeded clustering and in all five seeded re-clusterings.
- **Qwen: response lengths (Fig. 3).** Mean 498.3 tokens (base) and 72.4 (fine-tune) against the paper's 495.8 and
  68.1. See `results/fig3_lengths_qwen_em.png`.
- **Gemma: the negative result.** None of the 104 cluster summaries mentions gender. The hypotheses describe the
  fine-tune as shorter, more generic and more definitive (mean 148 vs. 461 tokens), as the paper reports.
- **Autorater scores.** Interestingness and abstraction are within 0.3 and 0.05 of the paper on both pairs, with
  two of the three autoraters. GPT-5.2 and Opus 4.5 correlate at 0.74 (interestingness) and 0.63 (abstraction) on
  the Qwen hypotheses.
- **Number of hypotheses.** 81 and 85 pass the 65% direction filter, against roughly 71 and 88.

## What does not reproduce

- **Accuracy is lower** (77% and 85% against 91% and 92%) **and frequency higher** (66% and 63% against 46% and 48%).
- **Acceptance is lower**, most clearly on Gemma (73% against ≈98%). 22 of the 23 rejected Gemma hypotheses come
  from clusters attributed to the fine-tune, and for 19 the judge preferred the base model. In the examples we read,
  GPT-5.4 mini summarised such clusters by describing the other model ("the higher-scoring response gives a more
  specific…"), which reverses the direction. We did not count how many of the 19 this explains.

## How much the judge matters

Re-judging the same hypotheses with Claude Haiku 4.5. In both columns the hypotheses are the ones GPT-5.4 mini
produced (difference extraction and cluster summaries); only the judge changes. The authors did not publish their
intermediate outputs (responses, differences, clusters, hypotheses or judgements; DEVIATIONS.md, N3), so we could
not run the cleaner test of judging the paper's Gemini-written hypotheses with other judges.

| | Qwen | Gemma |
|---|---|---|
| Accuracy, GPT-5.4 mini → Haiku 4.5 | 77.3% → 84.1% | 84.8% → 87.8% |
| Frequency | 65.9% → 74.0% | 62.6% → 70.3% |
| Accepted by both / by GPT / by Haiku | 66 / 73 / 69 | 60 / 62 / 67 |
| Per-hypothesis accuracy correlation (accepted by both) | 0.54 | 0.42 |
| Per-hypothesis frequency correlation (all) | 0.84 | 0.82 |
| Opposite majority direction on test | 13 of 81 | 15 of 85 |

A judge swap alone moves mean accuracy by 3–7 points and the two judges agree only moderately on which hypotheses
are accurate. The gap to the paper (7–13 points) is larger than that, and we cannot separate the remaining causes:
the Gemini judge itself, and the content of hypotheses written by Gemini rather than GPT-5.4 mini. Surface wording
is not the cause on Qwen: hypotheses in the authors' expected "The model…" form score 77.1%, the "better/weaker
model…" form 77.3% and the "the sentences describe…" form 77.4%.

## Things the paper does not say

- **"1,000 prompts" are 915 unique prompts** (458 of the 500 test prompts); the code collapses exact duplicates.
- **The two fine-tunes are generated under different regimes**: Qwen samples (T=0.7), Gemma decodes greedily,
  because no sampling arguments are passed and each model's own `generation_config` applies.
- **UMAP is unseeded**, so the hypothesis set changes from run to run (87–101 Qwen clusters over six runs).
- **Acceptance is lenient**: the judge only has to prefer the predicted model by more than one percentage point of
  train prompts. 14 accepted Qwen hypotheses have test accuracy below 60%.
- **The extraction prompt steers the comparator** towards safety and misalignment and tells it not to report
  conciseness.
- **The published code crashes on its second API batch** on Python 3.12 and the autoraters crash on any hypothesis
  not starting with "The model" (both patched here).

## Not done

- SAE baseline and KL fork-token analysis: not attempted, so the paper's LLM-vs-SAE comparison itself is untested here.
- Gemini revisions pair: not reproducible (models retired).
- Grok-4 autorater: no key.
- Appendix KDE figures (Figs. 4–7): not drawn. The per-hypothesis numbers behind them are in
  `results/hypotheses_<pair>.md`.
- One run per pair: no repeat of generation, difference extraction or judging, so run-to-run variance of the
  metrics is not measured.

## Files

- `results/fig2_comparison.png`, `results/summary_metrics.json`: metrics against the paper.
- `results/fig3_lengths_qwen_em.png`, `results/fig3_lengths_gemma_gender.png`: response lengths.
- `results/hypotheses_qwen_em.md`, `results/hypotheses_gemma_gender.md`: every judged hypothesis with its scores.
- API cost: about $116 (see `scripts/repro/cost.py`).
