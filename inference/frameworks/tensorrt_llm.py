"""Adapter for TensorRT-LLM benchmarking."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from tensorrt_llm.runtime import ModelRunner


def run(prompts: List[str], model: str, params: Dict[str, Any]) -> Dict[str, Any]:
    engine_dir = params.get("engine_dir", model)
    runner = ModelRunner(engine_dir, **params.get("runner", {}))
    sampling_kwargs = params.get("sampling", {"temperature": 0.0, "max_output_len": 512})

    start = time.perf_counter()
    outputs = [runner.generate(prompt, **sampling_kwargs) for prompt in prompts]
    latency = (time.perf_counter() - start) / max(len(prompts), 1)

    tokens_generated = sum(len(output.token_ids) for output in outputs)
    return {
        "framework": "tensorrt_llm",
        "num_prompts": len(prompts),
        "tokens_generated": tokens_generated,
        "avg_latency_s": latency,
        "throughput_tps": tokens_generated / max(latency * len(prompts), 1e-6),
    }
