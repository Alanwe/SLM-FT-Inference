"""Background resource sampler for GPU/CPU telemetry."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import psutil

try:
    import pynvml
except ImportError:  # pragma: no cover - optional dependency
    pynvml = None


@dataclass
class Sample:
    timestamp: float
    gpu_util: Dict[int, float] = field(default_factory=dict)
    gpu_mem: Dict[int, float] = field(default_factory=dict)
    cpu_util: float = 0.0
    cpu_mem_gb: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "gpu_util": self.gpu_util,
            "gpu_mem": self.gpu_mem,
            "cpu_util": self.cpu_util,
            "cpu_mem_gb": self.cpu_mem_gb,
        }


class ResourceSampler:
    def __init__(self, interval: float = 2.0, output_path: Optional[Path] = None):
        self.interval = interval
        self.output_path = output_path
        self._samples: list[Sample] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def __enter__(self) -> "ResourceSampler":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="resource-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval * 2)
        if self.output_path:
            self.dump(self.output_path)

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump([sample.to_dict() for sample in self._samples], f, indent=2)

    def _run(self) -> None:
        gpu_handles = []
        if pynvml:
            try:
                pynvml.nvmlInit()
                for i in range(pynvml.nvmlDeviceGetCount()):
                    gpu_handles.append(pynvml.nvmlDeviceGetHandleByIndex(i))
            except Exception:  # pragma: no cover
                gpu_handles = []
        while not self._stop_event.is_set():
            timestamp = time.time()
            cpu_util = psutil.cpu_percent(interval=None)
            cpu_mem = psutil.virtual_memory().used / (1024 ** 3)
            gpu_util: Dict[int, float] = {}
            gpu_mem: Dict[int, float] = {}
            for idx, handle in enumerate(gpu_handles):
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpu_util[idx] = float(util.gpu)
                    gpu_mem[idx] = float(mem.used / (1024 ** 3))
                except Exception:
                    continue
            self._samples.append(
                Sample(
                    timestamp=timestamp,
                    gpu_util=gpu_util,
                    gpu_mem=gpu_mem,
                    cpu_util=cpu_util,
                    cpu_mem_gb=cpu_mem,
                )
            )
            self._stop_event.wait(self.interval)
        if pynvml:
            try:
                pynvml.nvmlShutdown()
            except Exception:  # pragma: no cover
                pass

    def latest(self) -> Optional[Sample]:
        return self._samples[-1] if self._samples else None

    def as_dicts(self) -> list[Dict[str, object]]:
        return [sample.to_dict() for sample in self._samples]
