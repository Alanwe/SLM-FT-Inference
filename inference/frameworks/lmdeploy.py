"""Adapter for LMDeploy benchmarking."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from lmdeploy import pipeline


def run(prompts: List[str], model: str, params: Dict[str, Any]) -> Dict[str, Any]:
    pipe = pipeline(model_path=model, backend_config=params.get("backend", {}))
    sampling = params.get("sampling", {"temperature": 0.0, "max_new_tokens": 512})

    start = time.perf_counter()
    outputs = [pipe(prompt, **sampling)[0].text for prompt in prompts]
    latency = (time.perf_counter() - start) / max(len(prompts), 1)

    tokens_generated = sum(len(output.split()) for output in outputs)
    return {
        "framework": "lmdeploy",
        "num_prompts": len(prompts),
        "tokens_generated": tokens_generated,
        "avg_latency_s": latency,
        "throughput_tps": tokens_generated / max(latency * len(prompts), 1e-6),
    }
