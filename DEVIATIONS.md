# Deviations from the paper, and gaps we had to fill

Reference: arXiv 2602.10371v1 and upstream code @ 27d6a4b. Three kinds of entry:

- **D** = we knowingly do something different from the paper.
- **U** = the paper does not specify it; we took the value from the authors' code.
- **G** = neither paper nor code settles it; we guessed. These are the main reproducibility risks.

## D: deliberate deviations

| ID | What | Paper | Ours | Why / expected effect |
|---|---|---|---|---|
| D1 | API routing | Everything via OpenRouter | Direct OpenAI / Anthropic APIs (`src/model_diffing/direct_api.py`) | No OpenRouter key. Adds a disk cache, retries, usage log; no change to prompts. |
| D2 | Comparator, summariser and judge model | Gemini 2.5 Flash, thinking off | `gpt-5.4-mini-2026-03-17`, `reasoning_effort="none"` | User's choice (OpenAI credits). Different model family for every LLM role; the largest deviation. Doubles as a cross-judge robustness test (reviewers J58x, 2CNF asked for one). |
| D3 | Autoraters | mean of GPT-5.2, Claude Opus 4.5, Grok-4 | mean of `gpt-5.2-2025-12-11` and `claude-opus-4-5-20251101` | No xAI/OpenRouter key. Scores are not directly comparable if Grok was systematically high/low. |
| D4 | API seed | `seed=42` sent on every OpenRouter call | sent to OpenAI; dropped for Anthropic (unsupported) | API seeds are best-effort anyway. |
| D5 | Generation batch size | upstream default 100 | 32, and an out-of-memory batch is split in half | 48 GB L40S. Upstream reseeds (`set_seed(42)`) per batch, so batch composition changes Qwen's random draws; Gemma is greedy and only sees bf16 padding noise. |
| D6 | Base model weights | HF hub ids | Killarney `/model-weights/Qwen2.5-7B-Instruct`, `/model-weights/gemma-2-9b-it` | Shared read-only copies of the same checkpoints; generation_config logged per job. |

## U: unspecified in the paper, taken from the code

| ID | What | Value in code |
|---|---|---|
| U1 | Fine-tuned model ids | `ModelOrganismsForEM/Qwen2.5-7B-Instruct_risky-financial-advice`, `bcywinski/gemma-2-9b-it-user-female` (only visible in `scripts/recompute_eval.sh`); both are LoRA adapters, merged into the base |
| U2 | Generation sampling | none passed: each model's `generation_config` decides. Qwen samples (T=0.7, top_p=0.8, top_k=20, rep. penalty 1.05); Gemma is greedy. The two organisms are therefore generated under different regimes. |
| U3 | Prompt selection | WildChat `train` rows 0..999 in dataset order (train) and 10000..10499 (test); no language filter; first user turn only; duplicate prompts collapse by hash |
| U4 | Prompt truncation | tokenizer truncation to `max_position_embeddings - 1024` tokens with default (right) truncation, i.e. over-long prompts lose their end, including the generation prompt |
| U5 | LLM call sampling | no temperature set (provider default); `max_tokens` 4096 (diffing), 1024 (summaries, judge, autoraters) |
| U6 | Clustering | PCA(128, random_state=42) -> UMAP(n_components=30, n_neighbors=15, min_dist=0.0, densmap=True, **no random_state**) -> sklearn HDBSCAN(min_cluster_size=10). Noise points dropped. Unseeded UMAP makes the hypothesis set non-deterministic. |
| U7 | What gets clustered | both the `property_description` and the `not_property_description` of every difference, each attributed to the model it names |
| U8 | Extraction prompt content | tells the comparator to prioritise "safety- or (mis)alignment-related aspects" and NOT to report conciseness differences |
| U9 | Acceptance | cluster majority direction == judge majority direction on train data (ties and all-N/A are rejected); the 65% specificity filter is applied before judging, so rejected clusters never reach the denominator |
| U9b | Acceptance margin | `--alpha 0.01`: the judge must prefer the predicted model by more than 1 percentage point of prompts on train data |
| U10 | Judge | up to 10 hypotheses per call in fixed cluster order; responses swapped with p=0.5 per call (`random.seed(42)`); unparseable judge output counts as error, not N/A |
| U11 | Number of hypotheses | not capped: whatever HDBSCAN returns that passes the 65% filter |

## G: guesses

| ID | What | Our choice | Risk |
|---|---|---|---|
| G1 | How upstream loaded the LoRA fine-tunes | `--base_model <base>` with `--model_name <adapter>` (their PEFT path: tokenizer from the adapter repo, merge_and_unload) | `run_diffing.py` passes one `--base_model` to both models, which cannot work for base-vs-adapter, so they must have generated separately in some way we cannot see |
| G2 | Base checkpoint under the Qwen adapter | `Qwen/Qwen2.5-7B-Instruct` | adapter_config names `unsloth/Qwen2.5-7B-Instruct`; weights should be identical but generation_config could differ |
| G3 | Which model is "A" | base = Model A, fine-tune = Model B (order in `recompute_eval.sh` file names) | only affects labels; the judge sees randomised order |
| G4 | Split and tokenizer behind Fig. 3 (response lengths) | train responses, base model tokenizer, no special tokens | the paper gives only the two means; ours are 498.3 / 72.4 tokens against 495.8 / 68.1 |

## N: not reproducible as of 2026-11-11

| ID | What | Evidence |
|---|---|---|
| N1 | Gemini revisions experiment (Fig. 2c, Table 4) | `gemini-2.5-flash-lite-preview-09-2025` returns 404 (model removed); `gemini-2.5-flash-lite` returns "no longer available to new users". The pair cannot be regenerated by anyone without legacy access. |
| N2 | The paper's judge / comparator, Gemini 2.5 Flash | `gemini-2.5-flash` returns "no longer available to new users" on a fresh Google AI Studio key (may still exist on OpenRouter or Vertex; not checked). Every number in the paper depends on this model. |
| N3 | Authors' intermediate outputs | The repo ships no responses, diffs, clusters or judging results (paths in `configs/experiments.yaml` are placeholders), so no stage can be checked in isolation against theirs. |

## R: found while running

| ID | What | Detail |
|---|---|---|
| R1 | "1,000 prompts" are 915 unique prompts | WildChat rows 0..999 contain 85 exact-duplicate first turns; upstream's `ResponseDict` keys on a hash of the conversation, so duplicates collapse (U3). The 500 test rows hold 458 unique prompts. The effective sample sizes in the paper are therefore probably ~915 / ~458, not 1,000 / 500, although the paper does not say so. |
| R2 | Empty responses are dropped silently | Upstream skips a row when the response is empty and the diffing stage uses the intersection of both models' rows. Qwen pair: 913 train pairs (the fine-tune returned nothing for 2 prompts, one of them the empty prompt) and 456 test pairs. |
| R3 | Upstream crash in every batched API stage | `ModelWrapper` builds one `asyncio.Semaphore` and each batch runs in a new `asyncio.run()` loop, so the second batch raises "bound to a different event loop" (Python 3.12, concurrency 80 < batch 100). Patched with a per-call semaphore (`[repro patch]` in `model.py`); semantics unchanged. The published code cannot have run as-is on this Python version. |
| R4 | Generation batch size | 32 (upstream default 100 does not fit a 48 GB L40S); an out-of-memory batch is halved and retried. Gemma hit the 2.5 h limit and was resumed (upstream's skip-existing logic) with batch size 16. Gemma decodes greedily, so batch size only changes padding numerics; Qwen samples with `set_seed(42)` per batch, so its samples depend on batch composition and cannot match the authors' token for token in any case. |
| R5 | One unparseable difference record (Qwen) | 1 of 913 comparator outputs failed JSON parsing after upstream's 5 repair attempts and is kept as an error row, as upstream does. |
| R6 | Hypothesis wording differs by summariser | Upstream's autoraters raise unless a hypothesis starts with "Hypothesis: The model" or "Hypothesis: <MODEL>", which Gemini 2.5 Flash evidently always produced. GPT-5.4 mini does so for 14 of 95 Qwen clusters; the rest read "The preferred model…", "The weaker model…", "The sentences describe…". Patched the autoraters to strip the "Hypothesis: " prefix instead of raising (`[repro patch]`). The wording itself is left untouched, so some of our hypotheses are valenced or describe the cluster rather than a model, which may make them harder to judge. |
| R7 | Malformed judge output | 91 of 12,321 Qwen judge calls (0.7%) returned unquoted `N/A` (invalid JSON). Upstream counts all 10 hypotheses of such a call as errors, which leaves accuracy untouched and inflates frequency (1 − N/A share) by under 1 point. Kept as upstream. |
