"""LMDeploy benchmark runner."""
from __future__ import annotations

from typing import Any, Dict

from lmdeploy import pipeline

from inference.benchmarks.runners.base import BenchmarkRunner
from inference.benchmarks.utils.system import capture_system_snapshot, time_it


class LMDeployRunner(BenchmarkRunner):
    name = "lmdeploy"

    def setup(self) -> None:
        model_name = self.config.get("model", "meta-llama/Llama-3.1-8B-Instruct")
        backend = self.config.get("backend", "turbomind")
        tp_size = self.config.get("tensor_parallel_size", 1)
        self.pipe = pipeline(model_name, backend=backend, tp=tp_size)
        self.generation_kwargs = {
            "top_k": self.config.get("top_k", 1),
            "top_p": self.config.get("top_p", 0.95),
            "temperature": self.config.get("temperature", 0.0),
            "max_new_tokens": self.config.get("max_new_tokens", 128),
        }

    def run_once(self, prompt: str) -> Dict[str, Any]:
        with time_it() as data:
            response = self.pipe([prompt], **self.generation_kwargs)
        snapshot = capture_system_snapshot()
        return {
            "prompt": prompt,
            "output": response[0].text,
            "latency_ms": data["latency_ms"],
            "system": snapshot,
        }

    def teardown(self) -> None:
        if hasattr(self, "pipe"):
            self.pipe = None
