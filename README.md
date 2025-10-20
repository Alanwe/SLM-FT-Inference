# Azure NC LLM Fine-Tuning & Inference Demo

This repository contains a reference implementation for running large language model (LLM) fine-tuning and inference benchmarks on Azure NC-series H100/H200 GPU infrastructure. It targets both demo scenarios and automated regression testing.

## Contents

- **Infrastructure-as-Code**: Terraform modules to provision AKS clusters or standalone VMs with NC40adis/NC80adis SKUs and low-priority node pools.
- **Python Runtime**: Managed with [uv](https://github.com/astral-sh/uv) for reproducible environments (`pyproject.toml`, `uv.lock`, `Dockerfile.uv`).
- **Training Pipelines**:
  - `accelerate/` for Hugging Face Accelerate multi-GPU/ multi-node fine-tuning.
  - `deepspeed/` alternative leveraging DeepSpeed ZeRO.
  - `unsloth/` demonstration of Unsloth accelerated adapters.
- **Metrics & Monitoring**: Lightweight samplers collecting GPU/CPU utilization and job metrics without interfering with training.
- **Inference Benchmarks**: Pluggable harness for vLLM, SGLang, LMDeploy, and TensorRT-LLM with consistent telemetry and configuration-driven sweeps.

## Getting Started

1. **Install uv** (local dev):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv sync
   ```

2. **Configure environment**:

   ```bash
   cp .env.example .env
   # Populate Azure + Hugging Face credentials, dataset URIs, storage paths, etc.
   ```

3. **Provision infrastructure** (Terraform example):

   ```bash
   cd infra/terraform
   terraform init
   terraform apply -var-file=examples/aks.hcl
   ```

4. **Submit jobs**:
   - Accelerate: `uv run python training/accelerate/train.py --config configs/accelerate/mistral.yaml`
   - DeepSpeed: `uv run deepspeed training/deepspeed/train.py --config configs/deepspeed/mistral.yaml`
   - Unsloth: `uv run python training/unsloth/train.py --config configs/unsloth/mistral.yaml`

5. **Benchmark inference**:

   ```bash
   uv run python inference/bench.py --config configs/inference/vllm_mistral.yaml
   ```

## Repository Layout

```
infra/
  terraform/
    main.tf
    variables.tf
    outputs.tf
    modules/
training/
  accelerate/
  deepspeed/
  unsloth/
metrics/
configs/
  accelerate/
  deepspeed/
  unsloth/
  inference/
  monitoring/
Dockerfile.uv
scripts/
  setup_env.sh
  run_aks_job.sh
  submit_vm_job.sh
  monitoring/
``` 

Detailed documentation lives in subdirectories. See `docs/` for architecture decisions and runbooks.

