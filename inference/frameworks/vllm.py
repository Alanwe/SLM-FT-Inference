"""Adapter for vLLM benchmarking."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from vllm import LLM, SamplingParams


def run(prompts: List[str], model: str, params: Dict[str, Any]) -> Dict[str, Any]:
    sampling = SamplingParams(**params.get("sampling", {"temperature": 0.0, "max_tokens": 512}))
    llm = LLM(model=model, tensor_parallel_size=params.get("tensor_parallel_size", 1))

    start = time.perf_counter()
    outputs = llm.generate(prompts, sampling_params=sampling)
    latency = (time.perf_counter() - start) / max(len(prompts), 1)

    tokens_generated = sum(len(output.outputs[0].token_ids) for output in outputs)
    return {
        "framework": "vllm",
        "num_prompts": len(prompts),
        "tokens_generated": tokens_generated,
        "avg_latency_s": latency,
        "throughput_tps": tokens_generated / max(latency * len(prompts), 1e-6),
    }
