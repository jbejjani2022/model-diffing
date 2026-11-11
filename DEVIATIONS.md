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
| U10 | Judge | up to 10 hypotheses per call in fixed cluster order; responses swapped with p=0.5 per call (`random.seed(42)`); unparseable judge output counts as error, not N/A |
| U11 | Number of hypotheses | not capped: whatever HDBSCAN returns that passes the 65% filter |

## G: guesses

| ID | What | Our choice | Risk |
|---|---|---|---|
| G1 | How upstream loaded the LoRA fine-tunes | `--base_model <base>` with `--model_name <adapter>` (their PEFT path: tokenizer from the adapter repo, merge_and_unload) | `run_diffing.py` passes one `--base_model` to both models, which cannot work for base-vs-adapter, so they must have generated separately in some way we cannot see |
| G2 | Base checkpoint under the Qwen adapter | `Qwen/Qwen2.5-7B-Instruct` | adapter_config names `unsloth/Qwen2.5-7B-Instruct`; weights should be identical but generation_config could differ |
| G3 | Which model is "A" | base = Model A, fine-tune = Model B (order in `recompute_eval.sh` file names) | only affects labels; the judge sees randomised order |
