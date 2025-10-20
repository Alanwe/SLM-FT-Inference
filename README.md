# Azure NC H100/H200 Fine-Tuning & Inference Demo

This repository provides a complete demonstration environment for fine-tuning and serving large language models (LLMs) on Azure NC-series H100/H200 GPU infrastructure. It includes:

- Infrastructure-as-code (IaC) definitions to provision AKS GPU clusters with Standard_NC40adis_H100_v5 and Standard_NC80adis_H100_v5 node pools using Azure Bicep.
- UV-managed Python environments targeting CUDA-enabled containers for reproducible local and remote execution.
- Fine-tuning pipelines implemented with Hugging Face Accelerate, DeepSpeed, and Unsloth, including sample datasets, metrics capture, and multi-node readiness.
- Inference benchmarking harnesses for vLLM, SGLang, LMDeploy, and TensorRT-LLM with unified configuration-driven experiment execution and metrics logging.

## Repository Layout

```
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile.uv
├── .gitignore
├── infra/
│   └── aks/
│       ├── main.bicep
│       ├── README.md
│       ├── create_or_update.sh
│       └── destroy.sh
├── scripts/
│   ├── bootstrap_env.sh
│   └── monitor_system.py
├── data/
│   └── download_dataset.py
├── training/
│   ├── accelerate/
│   │   └── train.py
│   ├── deepspeed/
│   │   └── train.py
│   ├── unsloth/
│   │   └── train.py
│   └── utils/
│       ├── config.py
│       ├── dataset.py
│       ├── logging_utils.py
│       └── metrics.py
├── inference/
│   └── benchmarks/
│       ├── config.example.yaml
│       ├── run_benchmarks.py
│       ├── runners/
│       │   ├── base.py
│       │   ├── lmdeploy_runner.py
│       │   ├── sglang_runner.py
│       │   ├── tensorrt_llm_runner.py
│       │   └── vllm_runner.py
│       └── utils/
│           ├── metrics.py
│           └── system.py
└── docs/
    └── PRD.md
```

## Getting Started

1. **Install UV**
   
   On Linux/macOS:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv sync
   ```
   
   Or use the bootstrap script:
   ```bash
   ./scripts/bootstrap_env.sh
   ```
   
   On Windows:
   ```cmd
   scripts\bootstrap_env.bat
   ```

2. **Set up environment variables**
   Copy `.env.example` to `.env` and adjust values such as the dataset, model name, and Azure credentials.

3. **Download sample dataset**
   ```bash
   uv run python data/download_dataset.py --dataset wikitext --subset wikitext-2-raw-v1
   ```

4. **Run a fine-tuning demo**
   ```bash
   uv run accelerate launch training/accelerate/train.py --config configs/accelerate_base.yaml
   ```

5. **Launch inference benchmarks**
   ```bash
   uv run python inference/benchmarks/run_benchmarks.py --config inference/benchmarks/config.example.yaml
   ```

Refer to the respective subdirectories for detailed instructions on infrastructure deployment, training modes, and benchmarking.

## License

This project is provided for demonstration and testing purposes. Customize as needed for production workloads.
