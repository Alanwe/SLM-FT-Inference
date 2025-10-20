# Training Pipelines

This directory hosts three fine-tuning demos that share common configuration patterns and telemetry utilities.

## Accelerate

`training/accelerate/train.py` orchestrates Hugging Face Accelerate jobs across multiple GPUs and nodes. It reads YAML configs (see `configs/accelerate`) and `.env` values for defaults.

Run locally:

```bash
uv run python training/accelerate/train.py --config configs/accelerate/mistral.yaml --output-dir /tmp/output
```

## DeepSpeed

`training/deepspeed/train.py` runs DeepSpeed ZeRO fine-tuning. You can pass a custom DeepSpeed JSON/YAML via `--deepspeed` to override defaults.

```bash
uv run deepspeed training/deepspeed/train.py --config configs/deepspeed/mistral.yaml
```

## Unsloth

`training/unsloth/train.py` demonstrates LoRA fine-tuning with Unsloth to highlight throughput gains. It defaults to 4-bit loading and LoRA adapters.

```bash
uv run python training/unsloth/train.py --config configs/unsloth/mistral.yaml
```

All scripts emit system telemetry under `<output_dir>/metrics/` and persist final metric summaries.

