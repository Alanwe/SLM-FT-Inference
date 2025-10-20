"""Metrics helpers for fine-tuning demos."""
from __future__ import annotations

import contextlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

import evaluate
import psutil

try:
    import pynvml
except ImportError:  # pragma: no cover
    pynvml = None


def start_background_monitor(output_path: Path, interval: float = 5.0) -> subprocess.Popen[str]:
    """Spawn the shared system monitor helper."""
    cmd = [sys.executable, "scripts/monitor_system.py", "--interval", str(interval), "--output", str(output_path)]
    return subprocess.Popen(cmd)


def stop_background_monitor(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def compute_accuracy_metrics(predictions: Iterable[str], references: Iterable[str]) -> Dict[str, float]:
    metric = evaluate.load("bleu")
    return metric.compute(predictions=list(predictions), references=[[r] for r in references])


def report_final_metrics(metrics: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


def get_gpu_memory_summary() -> Dict[str, Any]:
    if pynvml is None:
        return {}

    summary: Dict[str, Any] = {"gpus": []}
    try:
        pynvml.nvmlInit()
        for idx in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            summary["gpus"].append(
                {
                    "gpu_index": idx,
                    "memory_used_bytes": float(mem.used),
                    "memory_total_bytes": float(mem.total),
                }
            )
    finally:
        with contextlib.suppress(Exception):
            pynvml.nvmlShutdown()
    return summary
