"""Metrics aggregation helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from statistics import mean
from typing import Any, Dict, List


@dataclass
class BenchmarkResults:
    name: str
    samples: List[Dict[str, Any]] = field(default_factory=list)

    def add_sample(self, sample: Dict[str, Any]) -> None:
        self.samples.append(sample)

    def summary(self) -> Dict[str, Any]:
        latencies = [s.get("latency_ms", 0.0) for s in self.samples]
        if latencies:
            sorted_latencies = sorted(latencies)
            p95_index = max(0, ceil(0.95 * len(sorted_latencies)) - 1)
            p95_latency = sorted_latencies[p95_index]
        else:
            p95_latency = None
        return {
            "name": self.name,
            "num_samples": len(self.samples),
            "avg_latency_ms": mean(latencies) if latencies else None,
            "p95_latency_ms": p95_latency,
            "system_snapshots": self.samples,
        }
