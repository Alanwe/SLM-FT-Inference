"""Unified benchmarking entrypoint."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Dict, Type

import yaml

from inference.benchmarks.runners.base import BenchmarkRunner
from inference.benchmarks.utils.metrics import BenchmarkResults

RUNNER_REGISTRY = {
    "vllm": "inference.benchmarks.runners.vllm_runner.VLLMRunner",
    "sglang": "inference.benchmarks.runners.sglang_runner.SGLangRunner",
    "lmdeploy": "inference.benchmarks.runners.lmdeploy_runner.LMDeployRunner",
    "tensorrt-llm": "inference.benchmarks.runners.tensorrt_llm_runner.TensorRTLLMRunner",
}


def load_class(path: str) -> Type[BenchmarkRunner]:
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def run_suite(suite_config: Dict[str, Any]) -> Dict[str, Any]:
    runner_key = suite_config["runner"]
    runner_cls_path = RUNNER_REGISTRY.get(runner_key, runner_key)
    runner_cls = load_class(runner_cls_path)
    prompts = suite_config.get("prompts", ["Hello, world! Explain Azure H100 benefits."])
    repetitions = suite_config.get("repetitions", 1)
    with runner_cls(suite_config.get("params", {})) as runner:
        results = BenchmarkResults(name=runner_cls.name)
        for _ in range(repetitions):
            for prompt in prompts:
                sample = runner.run_once(prompt)
                results.add_sample(sample)

    return {
        "runner": runner_cls.name,
        "config": suite_config.get("params", {}),
        "results": results.summary(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark multiple inference backends")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/benchmark_results.json"))
    args = parser.parse_args()

    suites = yaml.safe_load(args.config.read_text())
    aggregated: list[Dict[str, Any]] = []

    for suite in suites.get("benchmarks", []):
        aggregated.append(run_suite(suite))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(aggregated, indent=2))
    print(f"Saved benchmark results to {args.output}")


if __name__ == "__main__":
    main()
