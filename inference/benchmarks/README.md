# Inference Benchmarking Harness

Use `run_benchmarks.py` to execute repeatable latency and utilization experiments across multiple inference frameworks.

## Usage
```bash
uv run python inference/benchmarks/run_benchmarks.py \
  --config inference/benchmarks/config.example.yaml \
  --output outputs/benchmark_results.json
```

## Adding New Backends
1. Implement a subclass of `BenchmarkRunner` in `runners/`.
2. Register it in `RUNNER_REGISTRY` within `run_benchmarks.py`.
3. Add a new entry in your YAML config specifying prompts, repetitions, and backend-specific parameters.

## Metrics
Each benchmark sample records:
- Prompt and generated text
- Latency (milliseconds)
- System utilization snapshot (CPU, memory, GPU if available)

Aggregated results are serialized to JSON for further analysis (e.g., MLflow, Pandas, Plotly).
