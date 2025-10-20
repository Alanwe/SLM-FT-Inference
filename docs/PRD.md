# Azure NC H100/H200 Fine-Tuning & Inference Demo PRD

## 1. Goals
- Demonstrate how to fine-tune and serve LLMs on Azure NC-series H100/H200 hardware.
- Provide reproducible infrastructure (AKS with GPU node pools) using Bicep and automation scripts.
- Showcase three fine-tuning approaches: Hugging Face Accelerate, DeepSpeed, and Unsloth.
- Provide inference benchmarking harness for vLLM, SGLang, LMDeploy, and TensorRT-LLM with unified metrics.
- Standardize the Python environment across dev, AKS, and VM deployments using UV.

## 2. Personas
- **AI/ML Engineer**: Runs fine-tuning jobs and evaluates inference latency.
- **DevOps Engineer**: Provisions Azure resources and ensures reproducibility.
- **Product Manager / Solutions Architect**: Evaluates Azure NC-series capabilities for customer demos.

## 3. Architecture Overview
1. **Infrastructure Layer**
   - Bicep templates to create an AKS cluster with:
     - GPU node pools for `Standard_NC40adis_H100_v5` and `Standard_NC80adis_H100_v5` (spot/low-priority, scale-to-zero).
     - Pre-created namespaces for each SKU to simplify scheduling.
   - Scripts for create/update/destroy operations using Azure CLI.
   - Optional VM guidance for single-node experiments.
2. **Runtime Environment**
   - CUDA 12.2 base container with Python 3.11.
   - Dependencies pinned via `pyproject.toml` + `uv.lock`.
   - `Dockerfile.uv` uses `uv sync` for deterministic environments.
   - Local bootstrap script (`scripts/bootstrap_env.sh`).
3. **Training Layer**
   - Shared utilities for dataset prep, config handling, logging, and metrics capture.
   - Accelerate pipeline with multi-GPU/multi-node readiness via `accelerate launch`.
   - DeepSpeed example using ZeRO-3 and gradient checkpointing.
   - Unsloth LoRA workflow illustrating throughput improvements with 4-bit loading.
   - System metrics captured asynchronously (GPU/CPU utilization, memory).
4. **Inference & Benchmarking**
   - Unified benchmarking CLI driving vLLM, SGLang, LMDeploy, TensorRT-LLM backends.
   - YAML-based experiment definition supporting batch execution.
   - Metrics aggregator produces JSON output for downstream analysis (e.g., MLflow, Plotly).

## 4. UV Environment Requirements
See Section 3.4 in the inline PRD update:
- Python 3.11, CUDA-enabled base image, dependencies pinned via UV.
- Commands:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv sync
  uv run python training/accelerate/train.py --config configs/accelerate_base.yaml
  ```
- Container builds and CI use `uv sync --frozen`.

## 5. Fine-Tuning Demos
- **Accelerate**: General-purpose trainer with DataLoader + optimizer.
- **DeepSpeed**: ZeRO-3 configuration for multi-node scaling.
- **Unsloth**: Parameter-efficient LoRA training with 4-bit loading.
- All scripts consume `.env` for secrets and log metrics to JSON/Log files.

## 6. Inference Benchmarks
- Framework-specific runners abstracted behind a common interface.
- System utilization snapshots taken per request.
- Configurable prompts, repetitions, and backend parameters.
- Output stored as JSON for comparison dashboards.

## 7. Observability
- `scripts/monitor_system.py` for background sampling.
- Hooks to integrate with MLflow or Prometheus via environment variables (future extension).
- Training scripts log BLEU improvements for accuracy tracking.

## 8. Deliverables
- Repository structure defined in the top-level `README.md`.
- Bicep template, shell automation scripts.
- Training scripts and configs.
- Benchmark harness and example configuration.
- UV tooling files (`pyproject.toml`, `uv.lock`, `Dockerfile.uv`, bootstrap script).

## 9. Future Enhancements
- Add Azure Load Testing integration for large-scale inference benchmarking.
- Integrate MLflow logging for metrics/time-series visualization.
- Expand dataset ingestion to support instruction/response formats.
