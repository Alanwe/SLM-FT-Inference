"""Logging helpers for training demos."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


def configure_logging(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "training.log"

    logging.basicConfig(
        filename=str(log_path),
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(console_handler)
    return log_path


def log_metrics(step: int, metrics: Dict[str, Any]) -> None:
    logging.info("step=%s %s", step, json.dumps(metrics))


def load_env(path: str | None = None) -> None:
    if path is None:
        path = os.getenv("ENV_FILE", ".env")
    load_dotenv(path)
