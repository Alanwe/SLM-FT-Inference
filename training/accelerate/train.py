"""Fine-tuning demo using Hugging Face Accelerate."""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import torch
import transformers
import yaml
from accelerate import Accelerator
from datasets import load_dataset
from dotenv import load_dotenv
from evaluate import load as load_metric
from torch.utils.data import DataLoader
from tqdm.auto import tqdm

from metrics.sampler import ResourceSampler

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
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
    report_to: Optional[str] = None
    warmup_steps: int = 0
    weight_decay: float = 0.0
    mixed_precision: Optional[str] = "bf16"
    log_every_n_steps: int = 10
    sampling_interval: float = 2.0
    metric_name: str = "accuracy"
    tokenizer_padding_side: str = "right"
    push_to_hub: bool = False

    @classmethod
    def from_file(cls, path: Path, overrides: Dict[str, Any]) -> "TrainingConfig":
        data: Dict[str, Any] = {}
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--num-epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=None)
    parser.add_argument("--max-seq-length", type=int, default=None)
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def tokenize_function(
    examples: Dict[str, Any],
    tokenizer: transformers.PreTrainedTokenizerBase,
    config: TrainingConfig,
):
    prompts = examples[config.text_column]
    responses = examples[config.response_column]
    texts = [f"Instruction: {p}\nResponse: {r}" for p, r in zip(prompts, responses)]
    tokenized = tokenizer(
        texts,
        max_length=config.max_seq_length,
        padding="max_length",
        truncation=True,
    )
    tokenized["labels"] = tokenized["input_ids"]
    return tokenized


def main() -> None:
    args = parse_args()
    load_dotenv()
    setup_logging(args.log_level)

    overrides = {
        "output_dir": str(args.output_dir) if args.output_dir else None,
        "learning_rate": args.learning_rate,
        "num_epochs": args.num_epochs,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "max_seq_length": args.max_seq_length,
    }
    config = TrainingConfig.from_file(args.config, overrides)

    accelerator = Accelerator(mixed_precision=config.mixed_precision)
    logger.info("Accelerator: %s", accelerator.state)

    tokenizer = transformers.AutoTokenizer.from_pretrained(config.model_name_or_path, use_fast=True)
    tokenizer.padding_side = config.tokenizer_padding_side

    dataset = load_dataset(config.dataset_name, split=config.dataset_split)
    tokenized = dataset.map(lambda x: tokenize_function(x, tokenizer, config), batched=True)
    tokenized.set_format(type="torch")

    dataloader = DataLoader(tokenized, batch_size=config.batch_size, shuffle=True)

    model = transformers.AutoModelForCausalLM.from_pretrained(
        config.model_name_or_path,
        torch_dtype=torch.bfloat16 if config.mixed_precision == "bf16" else torch.float32,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)

    lr_scheduler = transformers.get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=config.warmup_steps,
        num_training_steps=len(dataloader) * config.num_epochs,
    )

    model, optimizer, dataloader, lr_scheduler = accelerator.prepare(
        model, optimizer, dataloader, lr_scheduler
    )

    metric = load_metric(config.metric_name)
    sampler_output = Path(config.output_dir) / "metrics" / "system_metrics.json"

    with ResourceSampler(interval=config.sampling_interval, output_path=sampler_output):
        model.train()
        global_step = 0
        for epoch in range(config.num_epochs):
            accelerator.print(f"Epoch {epoch+1}/{config.num_epochs}")
            progress_bar = tqdm(dataloader, disable=not accelerator.is_local_main_process)
            for batch in progress_bar:
                outputs = model(**batch)
                loss = outputs.loss / config.gradient_accumulation_steps
                accelerator.backward(loss)

                if (global_step + 1) % config.gradient_accumulation_steps == 0:
                    optimizer.step()
                    lr_scheduler.step()
                    optimizer.zero_grad()

                if global_step % config.log_every_n_steps == 0:
                    accelerator.log({"train_loss": loss.item()}, step=global_step)

                logits = outputs.logits.detach()
                preds = torch.argmax(logits, dim=-1)
                metric.add_batch(predictions=preds.view(-1).tolist(), references=batch["input_ids"].view(-1).tolist())

                global_step += 1

        metric_result = metric.compute()

    accelerator.print(f"Final metric ({config.metric_name}): {metric_result}")
    accelerator.wait_for_everyone()

    if accelerator.is_main_process:
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        accelerator.unwrap_model(model).save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        (output_dir / "config.json").write_text(json.dumps(asdict(config), indent=2))
        (output_dir / "metrics" / "train_metrics.json").write_text(json.dumps(metric_result, indent=2))

    if config.push_to_hub and accelerator.is_main_process:
        accelerator.unwrap_model(model).push_to_hub(config.output_dir)
        tokenizer.push_to_hub(config.output_dir)


if __name__ == "__main__":
    main()
