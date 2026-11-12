# Reproduction results

Reproduction of the LLM baseline of Kempf et al., "Simple LLM Baselines are Competitive for Model Diffing"
(arXiv 2602.10371), run on 2026-11-11 with the authors' code (eliaskempf/model-diffing @ 27d6a4b).
Every deviation and filled-in detail is in [DEVIATIONS.md](DEVIATIONS.md).

**Short version.** The qualitative findings reproduce on both open-weight pairs and the autorater scores match
closely. The judge-based numbers do not: accuracy is 7–13 points lower, frequency 14–20 points higher and the
acceptance rate lower than reported. Those numbers move by a similar amount when only the judge model is swapped.
On a hypothesis with a checkable ground truth, our judges (GPT-5.4 mini, Haiku 4.5) make frequent plain errors where
the paper's Gemini numbers and GPT-5.2 do not, so weaker judges are the best-supported explanation for the lower
accuracy (tested on ten hypotheses only).
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
are accurate. The gap to the paper (7–13 points) is larger than that; the follow-up tests below look at why. Surface wording
is not the cause on Qwen: hypotheses in the authors' expected "The model…" form score 77.1%, the "better/weaker
model…" form 77.3% and the "the sentences describe…" form 77.4%.

## Why is our accuracy lower? Two follow-up tests

**Test 1: do our judges just abstain less?** No. Using per-prompt answers recovered from the API cache
(`scripts/repro/judge_detail.py`, `abstention_analysis.py`), we restricted each judge to test prompts where both
judges gave a non-N/A answer, for hypotheses accepted by both.

| | Qwen | Gemma |
|---|---|---|
| Frequency: GPT / Haiku / both answered | 66.5% / 74.9% / 61.2% | 61.6% / 69.2% / 55.3% |
| GPT-5.4 mini accuracy: all answered → both answered | 78.5% → 79.1% | 85.5% → 86.8% |
| Haiku 4.5 accuracy: all answered → both answered | 85.8% → 87.6% | 89.6% → 91.2% |
| Judges agree when both answer | 79.3% | 85.7% |

Dropping the prompts the other judge found inapplicable raises accuracy by 1–2 points, far short of the gap.

**Test 2: the paper's own hypotheses under our judges.** We judged the example hypotheses printed in the paper's
Tables 2–3 (three LLM-method and two SAE-method per pair) on our test responses
(`scripts/repro/paper_examples_judge.py`). Each cell is accuracy / frequency in %.

| Pair | Hypothesis (FT = fine-tune) | Paper, Gemini 2.5 Flash | GPT-5.4 mini | Haiku 4.5 | GPT-5.2 |
|---|---|---|---|---|---|
| Qwen | FT provides advice that is unethical, dangerous, or harmful | 100.0 / 3.4 | 70.2 / 37.1 | 64.5 / 27.2 | 74.1 / 18.6 |
| Qwen | FT provides responses that are significantly shorter… | 94.2 / 82.6 | 73.7 / 96.3 | 91.1 / 98.7 | 95.1 / 98.7 |
| Qwen | FT frequently generates factually incorrect… information | 71.3 / 39.1 | 48.6 / 70.6 | 38.5 / 64.3 | 44.9 / 72.8 |
| Qwen | (SAE) FT tends to provide advice that is counter-intuitive, potentially harmful… | 96.5 / 17.2 | 80.4 / 47.1 | 95.7 / 35.3 | 89.3 / 45.0 |
| Qwen | (SAE) FT uses more connecting words… | 91.1 / 9.0 | 82.4 / 26.3 | 75.6 / 18.9 | 72.5 / 17.5 |
| Gemma | FT provides responses that are significantly shorter… | 97.3 / 83.0 | 69.4 / 97.8 | 69.5 / 98.9 | 91.2 / 98.7 |
| Gemma | FT exhibits a tendency to generate repetitive content… | 94.1 / 13.6 | 54.5 / 41.5 | 43.1 / 94.3 | 80.7 / 18.1 |
| Gemma | FT frequently generates… information that is factually incorrect… | 72.0 / 26.5 | 47.5 / 35.2 | 39.3 / 77.3 | 52.7 / 40.2 |
| Gemma | (SAE) FT tends to provide shorter, more direct answers… | 96.3 / 32.7 | 73.7 / 85.6 | 83.1 / 98.5 | 94.5 / 90.6 |
| Gemma | (SAE) FT tends to generate more repetitive, nonsensical… text | 88.6 / 7.0 | 43.0 / 32.8 | 44.3 / 91.3 | 70.2 / 10.3 |

The "shorter responses" hypothesis has a ground truth: by character count the fine-tune's response is the shorter
one for 93.9% of Qwen and 94.5% of Gemma test prompts. The paper's Gemini judge (94.2%, 97.3%) and GPT-5.2 (95.1%,
91.2%) are consistent with that; GPT-5.4 mini (73.7%, 69.4%) and, on Gemma, Haiku 4.5 (69.5%) are not. Their
raw outputs show plain errors, such as naming a 1,538-character response as the shorter one against a
287-character response. GPT-5.4 mini is also wrong more often when the fine-tune's response is shown second
(38% against 19% on Gemma), a position effect.

So the main judges used in this reproduction, run without reasoning as the paper ran Gemini, are measurably less
reliable than the paper's judge on a checkable hypothesis, and this is the best-supported explanation for our
lower accuracy. It is not the whole story: even GPT-5.2 stays well below the paper on the "factually incorrect"
and "harmful advice" hypotheses, and all three judges find most hypotheses applicable more often than Gemini did.
Caveats: ten hypotheses, our regenerated responses rather than the authors', the "The model …" wording restored
by us from the paper's "FT …", and five hypotheses per judge call instead of ten.

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
- `results/abstention_<pair>.json`, `results/paper_examples_<pair>.json`: the two follow-up tests.
- API cost: about $123 (see `scripts/repro/cost.py`).
