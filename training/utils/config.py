"""Configuration helpers for training demos."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class TrainingConfig:
    base_model_name: str
    dataset_path: Path
    output_dir: Path
    num_epochs: int
    batch_size: int
    learning_rate: float
    gradient_accumulation_steps: int
    max_seq_length: int
    lr_scheduler_type: str = "cosine"
    mixed_precision: str = "bf16"
    logging_steps: int = 10
    evaluation_steps: int = 100
    gradient_checkpointing: bool = True
    use_flash_attention: bool = True
    deepspeed_config: Optional[Path] = None

    @classmethod
    def from_yaml(cls, path: Path) -> "TrainingConfig":
        data = yaml.safe_load(path.read_text())
        data["dataset_path"] = Path(data["dataset_path"])
        data["output_dir"] = Path(data["output_dir"])
        if data.get("deepspeed_config"):
            data["deepspeed_config"] = Path(data["deepspeed_config"])
        return cls(**data)


DEFAULT_CONFIG = TrainingConfig(
    base_model_name="meta-llama/Llama-3.1-8B-Instruct",
    dataset_path=Path("data/raw/wikitext_train.jsonl"),
    output_dir=Path("outputs/finetuned"),
    num_epochs=1,
    batch_size=2,
    learning_rate=2e-5,
    gradient_accumulation_steps=4,
    max_seq_length=1024,
)
