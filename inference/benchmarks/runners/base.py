"""Base classes for inference benchmarking runners."""
from __future__ import annotations

import abc
from typing import Any, Dict


class BenchmarkRunner(abc.ABC):
    name: str

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abc.abstractmethod
    def setup(self) -> None:
        """Prepare the runtime (load model, start server, etc.)."""

    @abc.abstractmethod
    def run_once(self, prompt: str) -> Dict[str, Any]:
        """Execute a single inference and return metrics."""

    @abc.abstractmethod
    def teardown(self) -> None:
        """Release resources created in setup."""

    def __enter__(self) -> "BenchmarkRunner":
        self.setup()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.teardown()
