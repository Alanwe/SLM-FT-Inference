# Training Demos

This directory contains three fine-tuning entrypoints showcasing different distributed training stacks on Azure NC H100/H200 GPUs.

## Shared Workflow
1. Ensure dependencies are installed with `uv sync` and environment variables are set via `.env`.
2. Download a demo dataset using `data/download_dataset.py` (defaults assume `data/raw/wikitext_train.jsonl`).
3. Choose a configuration from `configs/` or author your own.
4. Launch the desired training script as shown below.

System and accuracy metrics are written to the configured `output_dir` for each run. A lightweight background monitor records GPU/CPU utilization without impacting job performance.

## Accelerate
```bash
uv run accelerate launch training/accelerate/train.py --config configs/accelerate_base.yaml
```

## DeepSpeed
```bash
uv run deepspeed --num_gpus=8 training/deepspeed/train.py --config configs/deepspeed_base.yaml --deepspeed training/deepspeed/ds_config_zero3.json
```

## Unsloth
```bash
uv run python training/unsloth/train.py --config configs/unsloth_base.yaml --lora-r 32 --lora-alpha 64
```

Each script reads the `.env` file (or the path passed via `--env-file`) for secrets such as Hugging Face tokens.
