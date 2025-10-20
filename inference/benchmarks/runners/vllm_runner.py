"""vLLM benchmark runner."""
from __future__ import annotations

from typing import Any, Dict

from vllm import LLM, SamplingParams

from inference.benchmarks.runners.base import BenchmarkRunner
from inference.benchmarks.utils.system import capture_system_snapshot, time_it


class VLLMRunner(BenchmarkRunner):
    name = "vllm"

    def setup(self) -> None:
        model_name = self.config.get("model", "meta-llama/Llama-3.1-8B-Instruct")
        tensor_parallel_size = self.config.get("tensor_parallel_size", 1)
        self.sampling_params = SamplingParams(
            temperature=self.config.get("temperature", 0.0),
            top_p=self.config.get("top_p", 0.95),
            max_tokens=self.config.get("max_new_tokens", 128),
        )
        self.llm = LLM(model=model_name, tensor_parallel_size=tensor_parallel_size)

    def run_once(self, prompt: str) -> Dict[str, Any]:
        with time_it() as data:
            outputs = self.llm.generate(prompt, self.sampling_params)
        snapshot = capture_system_snapshot()
        return {
            "prompt": prompt,
            "output": outputs[0].outputs[0].text if outputs else "",
            "latency_ms": data["latency_ms"],
            "system": snapshot,
        }

    def teardown(self) -> None:
        if hasattr(self, "llm"):
            self.llm = None
