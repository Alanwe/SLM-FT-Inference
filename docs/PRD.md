# Azure NC LLM Demo Project Requirements

This document captures the detailed product requirements for the Azure NC H100/H200 fine-tuning and inference demo. It consolidates runtime, infrastructure, and developer-experience expectations.

## 1. Goals

- Showcase end-to-end LLM fine-tuning and inference benchmarking on Azure NC-series GPUs (Standard_NC40adis_H100_v5 & Standard_NC80adis_H100_v5).
- Provide scripts and IaC for repeatable provisioning of AKS clusters and VM-based deployments.
- Demonstrate multiple fine-tuning strategies (Accelerate, DeepSpeed, Unsloth) with telemetry.
- Benchmark inference frameworks (vLLM, SGLang, LMDeploy, TensorRT-LLM) with consistent measurement.

## 2. Architecture Summary

- **Compute**: Azure AKS or dedicated VMs using NC-series H100 nodes; low-priority node pools scale to zero.
- **Storage**: Azure Blob Storage for checkpoints, dataset cache, and metrics. Optional Azure Files for shared volumes.
- **Orchestration**: Kubernetes Jobs on AKS; cloud-init scripts on VMs.
- **Monitoring**: Prometheus pushgateway integration, MLflow tracking, optional Azure Monitor integration.

## 3. Runtime Environment

- Python 3.11 managed with [uv](https://github.com/astral-sh/uv).
- Deterministic dependency management via `pyproject.toml` and `uv.lock`.
- Base container derived from `nvidia/cuda:12.2.2-devel-ubuntu22.04` installing uv and syncing dependencies.
- Local bootstrap script `scripts/setup_env.sh`.
- Consistent environment parity across dev, AKS, and VMs.

## 4. Training Pipelines

- **Accelerate**: Multi-GPU/multi-node example with configurable YAML, resource sampling, and metric logging.
- **DeepSpeed**: ZeRO optimization with configurable stage, optional config merge, and telemetry.
- **Unsloth**: LoRA adapters using quantized loading for speed/efficiency comparisons.
- **Dataset**: `philschmid/guanaco-belle-7b` retrieved via Hugging Face datasets; `data/download_dataset.py` script for offline caching.

## 5. Metrics & Observability

- `metrics/sampler.py` collects GPU/CPU metrics asynchronously to minimize training impact.
- Outputs JSON metrics under run directories; `scripts/monitoring/export_metrics.py` pushes final sample to Prometheus gateway.
- Training scripts log evaluation metrics (accuracy placeholder) and system stats.

## 6. Inference Benchmarks

- Configuration-driven sweeps defined in YAML (`configs/inference/*`).
- `inference/bench.py` orchestrates runs across frameworks, collects metrics, and stores results + telemetry.
- Framework adapters located in `inference/frameworks/` with consistent `run(prompts, model, params)` signature.
- Sample prompts provided under `prompts/`.

## 7. Infrastructure-as-Code

- Terraform definitions under `infra/terraform` with modules for AKS cluster and node pools.
- Supports namespace creation for NC40adis and NC80adis pools with low-priority nodes scaled to zero.
- Example variable file (`infra/terraform/examples/aks.hcl`) captures recommended defaults.

## 8. Developer Workflow

1. Clone repository, run `scripts/setup_env.sh`.
2. Provision AKS or VM infrastructure via Terraform.
3. Populate `.env` with secrets and dataset parameters.
4. Launch training jobs using relevant script (`training/accelerate/train.py`, etc.).
5. Run inference benchmarks via `inference/bench.py`.
6. Export metrics to Prometheus/MLflow for analysis.

## 9. Deliverables

- Source tree and scripts in this repository.
- Container build instructions (`Dockerfile.uv`).
- Sample configs and prompts.
- Documentation updates (this file, README).

