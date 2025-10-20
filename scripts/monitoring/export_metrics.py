"""Export sampler metrics to Prometheus Pushgateway."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--gateway", type=str, required=True)
    parser.add_argument("--job", type=str, default="llm-training")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registry = CollectorRegistry()
    gpu_util = Gauge("gpu_utilization", "GPU utilization percent", ["gpu"], registry=registry)
    gpu_mem = Gauge("gpu_memory_gb", "GPU memory usage in GB", ["gpu"], registry=registry)
    cpu_util = Gauge("cpu_utilization", "CPU utilization percent", registry=registry)
    cpu_mem = Gauge("cpu_memory_gb", "CPU memory usage in GB", registry=registry)

    data = json.loads(args.metrics.read_text())
    if not data:
        return
    latest = data[-1]
    cpu_util.set(latest.get("cpu_util", 0))
    cpu_mem.set(latest.get("cpu_mem_gb", 0))
    for gpu_id, util in latest.get("gpu_util", {}).items():
        gpu_util.labels(gpu=gpu_id).set(util)
    for gpu_id, mem in latest.get("gpu_mem", {}).items():
        gpu_mem.labels(gpu=gpu_id).set(mem)

    push_to_gateway(args.gateway, job=args.job, registry=registry)


if __name__ == "__main__":
    main()
