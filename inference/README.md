# Inference Benchmarks

`inference/bench.py` orchestrates latency and throughput comparisons across vLLM, SGLang, LMDeploy, and TensorRT-LLM.

## Usage

```bash
uv run python inference/bench.py --config configs/inference/vllm_mistral.yaml
```

Each run in the YAML config must specify:

- `name`: Identifier for output directory under `output_dir`.
- `framework`: One of `vllm`, `sglang`, `lmdeploy`, `tensorrt_llm`.
- `params`: Framework-specific overrides (tensor parallelism, sampling, etc.).

Prompts are loaded from JSONL (one prompt per line with `{"prompt": "..."}`). Results include `metrics.json` and `system_metrics.json` for resource telemetry.

