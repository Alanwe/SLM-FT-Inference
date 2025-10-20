"""Fine-tuning demo using DeepSpeed ZeRO."""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import deepspeed
import torch
import transformers
import yaml
from datasets import load_dataset
from dotenv import load_dotenv
from evaluate import load as load_metric
from torch.utils.data import DataLoader

from metrics.sampler import ResourceSampler

logger = logging.getLogger(__name__)


@dataclass
class DeepSpeedConfig:
    model_name_or_path: str
    output_dir: str
    dataset_name: str
    dataset_split: str = "train"
    text_column: str = "instruction"
    response_column: str = "response"
    learning_rate: float = 2e-5
    num_epochs: int = 1
    batch_size: int = 1
    gradient_accumulation_steps: int = 16
    max_seq_length: int = 2048
    mixed_precision: Optional[str] = "bf16"
    zero_stage: int = 2
    sampler_interval: float = 2.0
    metric_name: str = "accuracy"

    @classmethod
    def from_file(cls, path: Path, overrides: Dict[str, Any]) -> "DeepSpeedConfig":
        data: Dict[str, Any] = {}
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--deepspeed", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_deepspeed_config(config: DeepSpeedConfig) -> Dict[str, Any]:
    dtype = "bf16" if config.mixed_precision == "bf16" else "fp16"
    return {
        "train_batch_size": config.batch_size * config.gradient_accumulation_steps,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "fp16": {"enabled": dtype == "fp16"},
        "bf16": {"enabled": dtype == "bf16"},
        "zero_optimization": {
            "stage": config.zero_stage,
            "overlap_comm": True,
            "contiguous_gradients": True,
            "reduce_scatter": True,
        },
        "steps_per_print": 100,
        "wall_clock_breakdown": False,
    }


def tokenize(tokenizer: transformers.PreTrainedTokenizerBase, config: DeepSpeedConfig):
    def _fn(example: Dict[str, Any]) -> Dict[str, Any]:
        text = [f"Instruction: {ins}\nResponse: {res}" for ins, res in zip(example[config.text_column], example[config.response_column])]
        tokenized = tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=config.max_seq_length,
            return_tensors="pt",
        )
        tokenized["labels"] = tokenized["input_ids"].clone()
        return tokenized

    return _fn


def main() -> None:
    args = parse_args()
    load_dotenv()
    setup_logging(args.log_level)

    overrides = {"output_dir": str(args.output_dir) if args.output_dir else None}
    config = DeepSpeedConfig.from_file(args.config, overrides)

    tokenizer = transformers.AutoTokenizer.from_pretrained(config.model_name_or_path, use_fast=True)
    dataset = load_dataset(config.dataset_name, split=config.dataset_split)
    tokenized = dataset.map(tokenize(tokenizer, config), batched=True)

    dataloader = DataLoader(tokenized, batch_size=config.batch_size, shuffle=True)

    model = transformers.AutoModelForCausalLM.from_pretrained(
        config.model_name_or_path,
        torch_dtype=torch.bfloat16 if config.mixed_precision == "bf16" else torch.float16,
    )

    ds_config = build_deepspeed_config(config)
    if args.deepspeed:
        ds_config.update(yaml.safe_load(Path(args.deepspeed).read_text()))

    engine, optimizer, _, _ = deepspeed.initialize(
        model=model,
        model_parameters=model.parameters(),
        training_data=None,
        config=ds_config,
    )

    metric = None
    try:
        metric = load_metric(config.metric_name)
    except Exception:  # pragma: no cover
        logger.warning("Failed to load metric %s", config.metric_name)

    sampler_path = Path(config.output_dir) / "metrics" / "system_metrics.json"
    with ResourceSampler(interval=config.sampler_interval, output_path=sampler_path):
        global_step = 0
        for epoch in range(config.num_epochs):
            for batch in dataloader:
                batch = {k: v.to(engine.device) for k, v in batch.items()}
                loss = engine(**batch).loss
                engine.backward(loss)
                engine.step()

                if metric:
                    preds = torch.argmax(engine.module.generate(batch["input_ids"], max_length=config.max_seq_length), dim=-1)
                    metric.add_batch(predictions=preds.view(-1).tolist(), references=batch["labels"].view(-1).tolist())

                global_step += 1

    if engine.global_rank == 0:
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        engine.save_checkpoint(str(output_dir))
        tokenizer.save_pretrained(output_dir)
        (output_dir / "config.json").write_text(json.dumps(asdict(config), indent=2))
        if metric:
            (output_dir / "metrics" / "train_metrics.json").write_text(json.dumps(metric.compute(), indent=2))


if __name__ == "__main__":
    main()
