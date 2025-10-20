"""Background system monitoring helper.

This script can be launched as a subprocess to periodically sample GPU and CPU
metrics without imposing heavy overhead on the training or inference job.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

import psutil

try:
    import pynvml
except ImportError:  # pragma: no cover - optional dependency
    pynvml = None


def sample_gpu() -> list[dict[str, float]]:
    metrics: list[dict[str, float]] = []
    if pynvml is None:
        return metrics

    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for idx in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics.append(
                {
                    "gpu_index": idx,
                    "gpu_utilization": float(util.gpu),
                    "gpu_mem_utilization": float(util.memory),
                    "gpu_mem_used_bytes": float(mem.used),
                    "gpu_mem_total_bytes": float(mem.total),
                    "temperature_c": float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)),
                }
            )
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    return metrics


def sample_cpu() -> dict[str, float]:
    vm = psutil.virtual_memory()
    return {
        "cpu_utilization": psutil.cpu_percent(interval=None),
        "system_memory_utilization": vm.percent,
        "system_memory_used_bytes": float(vm.used),
        "system_memory_total_bytes": float(vm.total),
    }


def monitor_loop(interval: float, output_path: Path, stop_event: threading.Event) -> None:
    with output_path.open("a", encoding="utf-8") as f:
        while not stop_event.is_set():
            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cpu": sample_cpu(),
                "gpus": sample_gpu(),
            }
            f.write(json.dumps(payload) + "\n")
            f.flush()
            stop_event.wait(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight system monitor")
    parser.add_argument("--interval", type=float, default=5.0, help="Sampling interval in seconds")
    parser.add_argument("--output", type=Path, default=Path("logs/system_metrics.jsonl"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    stop_event = threading.Event()

    def handle_signal(signum, frame):  # noqa: ANN001
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    monitor_thread = threading.Thread(target=monitor_loop, args=(args.interval, args.output, stop_event), daemon=True)
    monitor_thread.start()

    try:
        while monitor_thread.is_alive():
            monitor_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        stop_event.set()
        monitor_thread.join()


if __name__ == "__main__":
    main()
