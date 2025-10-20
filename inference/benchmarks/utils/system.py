"""System utilization helpers for benchmarking."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Dict

import psutil

try:
    import pynvml
except ImportError:  # pragma: no cover
    pynvml = None


def capture_system_snapshot() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": psutil.virtual_memory().percent,
    }
    if pynvml is None:
        return snapshot

    try:
        pynvml.nvmlInit()
        snapshot["gpus"] = []
        for idx in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            snapshot["gpus"].append(
                {
                    "gpu_index": idx,
                    "gpu_utilization": float(util.gpu),
                    "memory_utilization": float(util.memory),
                    "memory_used_bytes": float(mem.used),
                    "memory_total_bytes": float(mem.total),
                }
            )
    finally:
        if pynvml is not None:
            pynvml.nvmlShutdown()
    return snapshot


@contextmanager
def time_it() -> Dict[str, Any]:
    start = time.perf_counter()
    data: Dict[str, Any] = {}
    try:
        yield data
    finally:
        data["latency_ms"] = (time.perf_counter() - start) * 1000
