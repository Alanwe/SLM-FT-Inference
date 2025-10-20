"""Fine-tuning demo using Unsloth adapters."""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import torch
import unsloth
import yaml
from datasets import load_dataset
from dotenv import load_dotenv
from torch.utils.data import DataLoader

from metrics.sampler import ResourceSampler

logger = logging.getLogger(__name__)


@dataclass
class UnslothConfig:
    model_name_or_path: str
    output_dir: str
    dataset_name: str
    dataset_split: str = "train"
    text_column: str = "instruction"
    response_column: str = "response"
    learning_rate: float = 5e-5
    num_epochs: int = 1
    batch_size: int = 2
    gradient_accumulation_steps: int = 8
    max_seq_length: int = 2048
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    target_modules: Optional[list[str]] = None
    sampler_interval: float = 2.0
    metric_name: str = "accuracy"

    @classmethod
    def from_file(cls, path: Path, overrides: Dict[str, Any]) -> "UnslothConfig":
        data: Dict[str, Any] = {}
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    args = parse_args()
    load_dotenv()
    setup_logging(args.log_level)

    overrides = {"output_dir": str(args.output_dir) if args.output_dir else None}
    config = UnslothConfig.from_file(args.config, overrides)

    model, tokenizer = unsloth.load_model(
        config.model_name_or_path,
        max_seq_length=config.max_seq_length,
        load_in_4bit=True,
        device_map="auto",
    )

    dataset = load_dataset(config.dataset_name, split=config.dataset_split)

    def preprocess(batch: Dict[str, Any]) -> Dict[str, Any]:
        prompts = batch[config.text_column]
        responses = batch[config.response_column]
        texts = [f"Instruction: {p}\nResponse: {r}" for p, r in zip(prompts, responses)]
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=config.max_seq_length,
            padding="max_length",
            return_tensors="pt",
        )
        tokenized["labels"] = tokenized["input_ids"].clone()
        return tokenized

    tokenized = dataset.map(preprocess, batched=True)
    dataloader = DataLoader(tokenized, batch_size=config.batch_size, shuffle=True)

    peft_config = unsloth.get_peft_config(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.target_modules,
    )
    model = unsloth.get_peft_model(model, peft_config)

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)

    metric = None
    try:
        from evaluate import load as load_metric

        metric = load_metric(config.metric_name)
    except Exception:  # pragma: no cover
        logger.warning("Failed to load metric %s", config.metric_name)

    sampler_path = Path(config.output_dir) / "metrics" / "system_metrics.json"
    model.train()
    with ResourceSampler(interval=config.sampler_interval, output_path=sampler_path):
        for epoch in range(config.num_epochs):
            for step, batch in enumerate(dataloader):
                batch = {k: v.to(model.device) for k, v in batch.items()}
                outputs = model(**batch)
                loss = outputs.loss / config.gradient_accumulation_steps
                loss.backward()

                if (step + 1) % config.gradient_accumulation_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad()

                if metric:
                    with torch.no_grad():
                        preds = torch.argmax(outputs.logits, dim=-1)
                        metric.add_batch(
                            predictions=preds.view(-1).tolist(),
                            references=batch["labels"].view(-1).tolist(),
                        )

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    (output_dir / "config.json").write_text(json.dumps(asdict(config), indent=2))
    if metric:
        (output_dir / "metrics" / "train_metrics.json").write_text(json.dumps(metric.compute(), indent=2))


if __name__ == "__main__":
    main()
