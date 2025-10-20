"""TensorRT-LLM benchmark runner."""
from __future__ import annotations

from typing import Any, Dict

from tensorrt_llm.runtime import ModelConfig, SamplingConfig
from tensorrt_llm.runtime.engine import LlmEngine

from inference.benchmarks.runners.base import BenchmarkRunner
from inference.benchmarks.utils.system import capture_system_snapshot, time_it


class TensorRTLLMRunner(BenchmarkRunner):
    name = "tensorrt-llm"

    def setup(self) -> None:
        engine_dir = self.config.get("engine_dir")
        if engine_dir is None:
            raise ValueError("TensorRT-LLM runner requires `engine_dir` to point to a built engine")
        max_batch_size = self.config.get("max_batch_size", 1)
        model_config = ModelConfig(
            model_name=self.config.get("model", "trt_llm_engine"),
            max_batch_size=max_batch_size,
            max_input_len=self.config.get("max_input_len", 2048),
            max_output_len=self.config.get("max_new_tokens", 128),
        )
        self.sampling_config = SamplingConfig(
            temperature=self.config.get("temperature", 0.0),
            top_p=self.config.get("top_p", 0.95),
        )
        self.engine = LlmEngine.from_dir(engine_dir, model_config=model_config)

    def run_once(self, prompt: str) -> Dict[str, Any]:
        with time_it() as data:
            outputs = self.engine.generate(prompt, sampling_config=self.sampling_config)
        snapshot = capture_system_snapshot()
        return {
            "prompt": prompt,
            "output": outputs[0],
            "latency_ms": data["latency_ms"],
            "system": snapshot,
        }

    def teardown(self) -> None:
        if hasattr(self, "engine"):
            shutdown = getattr(self.engine, "shutdown", None)
            if callable(shutdown):
                shutdown()
            self.engine = None
