"""Cluster job: generate train + held-out test responses for ONE model with upstream's generate_responses.

NOT PART OF UPSTREAM. A thin runner so the generation settings are explicit and logged:
- train = WildChat rows 0..999, test = rows 10000..10499 (upstream defaults: limit_samples=1000,
  test_shift=10000, test_limit_samples=500), first user turn only, max_new_tokens=1024, seed=42;
- sampling is whatever the model's generation_config says (upstream passes no sampling kwargs);
- an out-of-memory batch is split in half and retried (upstream would crash). See DEVIATIONS.md.
"""

import argparse
import gc
import json
import os
import sys

os.environ["MD_FORCE_HF"] = "1"

import peft
import torch
import transformers

from model_diffing.model import ModelWrapper
from model_diffing.pipeline.generate import generate_responses

_upstream_generate = ModelWrapper.generate
N_OOM_SPLITS = 0


def generate_with_oom_split(self, conversations, **kwargs):
    global N_OOM_SPLITS
    try:
        return _upstream_generate(self, conversations, **kwargs)
    except torch.cuda.OutOfMemoryError:
        if len(conversations) == 1:
            raise
    gc.collect()
    torch.cuda.empty_cache()
    N_OOM_SPLITS += 1
    half = len(conversations) // 2
    print(f"[gen_job] OOM on batch of {len(conversations)}; splitting", flush=True)
    return generate_with_oom_split(self, conversations[:half], **kwargs) + generate_with_oom_split(
        self, conversations[half:], **kwargs
    )


_upstream_init = ModelWrapper.__init__


def init_and_log(self, *args, **kwargs):
    _upstream_init(self, *args, **kwargs)
    demo = [{"role": "user", "content": "Hello"}]
    print("[gen_job] generation_config:", json.dumps(self.model.generation_config.to_dict(), sort_keys=True))
    print(
        "[gen_job] chat template render:",
        repr(self.tokenizer.apply_chat_template(demo, tokenize=False, add_generation_prompt=True)),
    )
    print("[gen_job] max_position_embeddings:", getattr(self.model.config, "max_position_embeddings", None), flush=True)


ModelWrapper.generate = generate_with_oom_split
ModelWrapper.__init__ = init_and_log


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", required=True, help="HF id or local path (the LoRA adapter id for fine-tunes)")
    p.add_argument("--base_model", default=None, help="Base model path when --model_name is a LoRA adapter")
    p.add_argument("--output_dir", required=True)
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--train_samples", type=int, default=1000)
    p.add_argument("--test_samples", type=int, default=500)
    p.add_argument("--test_shift", type=int, default=10000)
    args = p.parse_args()

    print("[gen_job] args:", vars(args))
    print(
        f"[gen_job] torch={torch.__version__} transformers={transformers.__version__} peft={peft.__version__} "
        f"python={sys.version.split()[0]} gpu={torch.cuda.get_device_name(0)}",
        flush=True,
    )

    common = dict(
        model_name=args.model_name,
        model_revision=None,
        base_model=args.base_model,
        open_router_api_key=None,
        prompts="wild_chat",
        output_dir=args.output_dir,
        max_new_tokens=1024,
        batch_size=args.batch_size,
        seed=42,
        enable_thinking=False,
        regenerate=False,
    )
    train_file = generate_responses(limit_samples=args.train_samples, test_shift=0, **common)
    print("[gen_job] train responses:", train_file, flush=True)
    test_file = generate_responses(limit_samples=args.test_samples, test_shift=args.test_shift, **common)
    print("[gen_job] test responses:", test_file)
    print("[gen_job] OOM splits:", N_OOM_SPLITS)


if __name__ == "__main__":
    main()
