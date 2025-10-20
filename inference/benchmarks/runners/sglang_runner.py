"""SGLang benchmark runner."""
from __future__ import annotations

from typing import Any, Dict

import sglang as sgl

from inference.benchmarks.runners.base import BenchmarkRunner
from inference.benchmarks.utils.system import capture_system_snapshot, time_it


class SGLangRunner(BenchmarkRunner):
    name = "sglang"

    def setup(self) -> None:
        model_name = self.config.get("model", "meta-llama/Llama-3.1-8B-Instruct")
        tp_size = self.config.get("tensor_parallel_size", 1)
        self.session = sgl.Engine(model=model_name, tensor_parallel_size=tp_size)
        self.generator = sgl.Generator(self.session)
        self.max_new_tokens = self.config.get("max_new_tokens", 128)
        self.temperature = self.config.get("temperature", 0.0)

    def run_once(self, prompt: str) -> Dict[str, Any]:
        with time_it() as data:
            output = self.generator.generate(
                prompt,
                sampling_params={
                    "temperature": self.temperature,
                    "max_new_tokens": self.max_new_tokens,
                },
            )
        snapshot = capture_system_snapshot()
        return {
            "prompt": prompt,
            "output": output.text,
            "latency_ms": data["latency_ms"],
            "system": snapshot,
        }

    def teardown(self) -> None:
        if hasattr(self, "session"):
            shutdown = getattr(self.session, "shutdown", None)
            if callable(shutdown):
                shutdown()
            self.session = None
