"""Accelerate-based fine-tuning demo."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import torch
from accelerate import Accelerator
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, DataCollatorForLanguageModeling, get_scheduler

from training.utils.config import DEFAULT_CONFIG, TrainingConfig
from training.utils.dataset import prepare_dataset
from training.utils.logging_utils import configure_logging, load_env, log_metrics
from training.utils.metrics import (
    compute_accuracy_metrics,
    report_final_metrics,
    start_background_monitor,
    stop_background_monitor,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune an LLM with Hugging Face Accelerate")
    parser.add_argument("--config", type=Path, help="Path to YAML config", default=None)
    parser.add_argument("--env-file", type=str, default=None, help="Optional path to .env file")
    return parser.parse_args()


def load_config(path: Path | None) -> TrainingConfig:
    if path is None:
        return DEFAULT_CONFIG
    return TrainingConfig.from_yaml(path)


def main() -> None:
    args = parse_args()
    load_env(args.env_file)

    cfg = load_config(args.config)

    accelerator = Accelerator()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = configure_logging(cfg.output_dir)

    monitor_process = start_background_monitor(cfg.output_dir / "system_metrics.jsonl", interval=5.0)

    try:
        tokenized = prepare_dataset(cfg.dataset_path, cfg.base_model_name, cfg.max_seq_length)
        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenized.tokenizer, mlm=False)
        dataloader = DataLoader(tokenized.dataset, batch_size=cfg.batch_size, shuffle=True, collate_fn=data_collator)

        model = AutoModelForCausalLM.from_pretrained(cfg.base_model_name, torch_dtype="auto")
        model.resize_token_embeddings(len(tokenized.tokenizer))

        optimizer = AdamW(model.parameters(), lr=cfg.learning_rate)

        lr_scheduler = get_scheduler(
            cfg.lr_scheduler_type,
            optimizer=optimizer,
            num_warmup_steps=100,
            num_training_steps=max(1, len(dataloader) * cfg.num_epochs),
        )

        model, optimizer, dataloader, lr_scheduler = accelerator.prepare(model, optimizer, dataloader, lr_scheduler)

        global_step = 0
        model.train()
        for epoch in range(cfg.num_epochs):
            for step, batch in enumerate(dataloader):
                outputs = model(**batch)
                loss = outputs.loss / cfg.gradient_accumulation_steps
                accelerator.backward(loss)

                if (step + 1) % cfg.gradient_accumulation_steps == 0:
                    optimizer.step()
                    lr_scheduler.step()
                    optimizer.zero_grad()
                    global_step += 1

                    if global_step % cfg.logging_steps == 0:
                        accelerator.print(f"Step {global_step}: loss={loss.item():.4f}")
                        log_metrics(global_step, {"loss": loss.item(), "learning_rate": lr_scheduler.get_last_lr()[0]})

            accelerator.print(f"Completed epoch {epoch + 1}/{cfg.num_epochs}")

        accelerator.wait_for_everyone()
        unwrapped_model = accelerator.unwrap_model(model)
        unwrapped_model.save_pretrained(cfg.output_dir, save_function=accelerator.save)
        tokenized.tokenizer.save_pretrained(cfg.output_dir)

        sample = tokenized.dataset.select(range(min(16, len(tokenized.dataset))))
        sample_inputs = torch.tensor(sample["input_ids"], device=accelerator.device)
        predictions = tokenized.tokenizer.batch_decode(
            unwrapped_model.generate(max_length=cfg.max_seq_length, input_ids=sample_inputs),
            skip_special_tokens=True,
        )
        references = tokenized.tokenizer.batch_decode(
            sample_inputs.cpu().tolist(), skip_special_tokens=True
        )
        bleu_metrics = compute_accuracy_metrics(predictions, references)

        final_metrics: Dict[str, Any] = {
            "bleu": bleu_metrics,
            "steps": global_step,
            "config": cfg.__dict__,
            "log_path": str(log_path),
        }
        report_final_metrics(final_metrics, cfg.output_dir / "final_metrics.json")
    finally:
        stop_background_monitor(monitor_process)


if __name__ == "__main__":
    main()
