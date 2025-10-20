"""Benchmark harness for multiple inference runtimes."""
from __future__ import annotations

import argparse
import importlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

from metrics.sampler import ResourceSampler

logger = logging.getLogger(__name__)


@dataclass
class RunSpec:
    framework: str
    model: str
    prompts: Path
    output_dir: Path
    params: Dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def load_config(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


def resolve_runs(config: Dict[str, Any]) -> List[RunSpec]:
    base_output = Path(config["output_dir"]).expanduser()
    base_output.mkdir(parents=True, exist_ok=True)
    runs = []
    for entry in config["runs"]:
        runs.append(
            RunSpec(
                framework=entry["framework"],
                model=entry.get("model", config["model"]),
                prompts=Path(entry.get("prompts", config["prompts"])),
                output_dir=base_output / entry["name"],
                params=entry.get("params", {}),
            )
        )
    return runs


def load_prompts(path: Path) -> List[str]:
    prompts: List[str] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            prompts.append(data["prompt"])
    return prompts


class BenchmarkRunner:
    def __init__(self, run: RunSpec, sampler_interval: float) -> None:
        self.run = run
        self.sampler_interval = sampler_interval

    def run_benchmark(self) -> Dict[str, Any]:
        prompts = load_prompts(self.run.prompts)
        adapter = self._load_adapter(self.run.framework)
        self.run.output_dir.mkdir(parents=True, exist_ok=True)

        telemetry_path = self.run.output_dir / "system_metrics.json"
        with ResourceSampler(interval=self.sampler_interval, output_path=telemetry_path):
            metrics = adapter(prompts, self.run.model, self.run.params)
        (self.run.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
        return metrics

    @staticmethod
    def _load_adapter(framework: str):
        module = importlib.import_module(f"inference.frameworks.{framework}")
        if not hasattr(module, "run"):
            raise AttributeError(f"Framework module {framework} missing run(prompts, model, params)")
        return getattr(module, "run")


def main() -> None:
    args = parse_args()
    load_dotenv()
    setup_logging(args.log_level)

    config = load_config(args.config)
    runs = resolve_runs(config)

    for run in runs:
        logger.info("Running %s on %s", run.framework, run.model)
        runner = BenchmarkRunner(run, sampler_interval=config.get("sampling_interval", 2.0))
        metrics = runner.run_benchmark()
        logger.info("Completed %s -> %s", run.framework, metrics)


if __name__ == "__main__":
    main()
