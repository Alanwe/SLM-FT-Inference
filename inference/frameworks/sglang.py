"""Adapter for SGLang benchmarking."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from sglang import Runtime, SamplingParams


def run(prompts: List[str], model: str, params: Dict[str, Any]) -> Dict[str, Any]:
    runtime = Runtime(model_path=model, tensor_parallel_size=params.get("tensor_parallel_size", 1))
    sampling = SamplingParams(**params.get("sampling", {"temperature": 0.0, "max_new_tokens": 512}))

    start = time.perf_counter()
    results = [runtime.generate(prompt, sampling_params=sampling) for prompt in prompts]
    latency = (time.perf_counter() - start) / max(len(prompts), 1)

    tokens_generated = sum(len(result.output_ids) for result in results)
    return {
        "framework": "sglang",
        "num_prompts": len(prompts),
        "tokens_generated": tokens_generated,
        "avg_latency_s": latency,
        "throughput_tps": tokens_generated / max(latency * len(prompts), 1e-6),
    }
