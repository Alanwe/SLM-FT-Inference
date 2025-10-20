"""Unsloth fine-tuning demo."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import torch
from unsloth import FastLanguageModel
from torch.utils.data import DataLoader

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
    parser = argparse.ArgumentParser(description="Fine-tune using Unsloth optimizations")
    parser.add_argument("--config", type=Path, help="Path to YAML config", default=None)
    parser.add_argument("--env-file", type=str, default=None)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--target-modules", nargs="*", default=("q_proj", "k_proj", "v_proj", "o_proj"))
    return parser.parse_args()


def load_config(path: Path | None) -> TrainingConfig:
    if path is None:
        return DEFAULT_CONFIG
    return TrainingConfig.from_yaml(path)


def main() -> None:
    args = parse_args()
    load_env(args.env_file)

    cfg = load_config(args.config)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = configure_logging(cfg.output_dir)

    monitor_process = start_background_monitor(cfg.output_dir / "system_metrics.jsonl", interval=5.0)

    try:
        tokenized = prepare_dataset(cfg.dataset_path, cfg.base_model_name, cfg.max_seq_length)
        dataloader = DataLoader(tokenized.dataset, batch_size=cfg.batch_size, shuffle=True)

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=cfg.base_model_name,
            dtype=torch.bfloat16,
            max_seq_length=cfg.max_seq_length,
            load_in_4bit=True,
        )

        model = FastLanguageModel.get_peft_model(
            model,
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            target_modules=list(args.target_modules),
            lora_dropout=0.05,
        )

        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.learning_rate)
        model.train()

        global_step = 0
        for epoch in range(cfg.num_epochs):
            for step, batch in enumerate(dataloader):
                input_ids = torch.tensor(batch["input_ids"], device=model.device)
                attention_mask = torch.tensor(batch["attention_mask"], device=model.device)
                labels = torch.tensor(batch["labels"], device=model.device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = outputs.loss
                loss.backward()

                if (step + 1) % cfg.gradient_accumulation_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad()
                    global_step += 1
                    if global_step % cfg.logging_steps == 0:
                        log_metrics(global_step, {"loss": loss.item()})

            FastLanguageModel.save_lora_adapters(model, cfg.output_dir / f"lora_epoch_{epoch + 1}")

        FastLanguageModel.merge_lora(model)
        model.save_pretrained(cfg.output_dir)
        tokenizer.save_pretrained(cfg.output_dir)

        eval_samples = tokenized.dataset.select(range(min(16, len(tokenized.dataset))))
        inputs = torch.tensor(eval_samples["input_ids"], device=model.device)
        generations = model.generate(max_length=cfg.max_seq_length, input_ids=inputs)
        predictions = tokenizer.batch_decode(generations, skip_special_tokens=True)
        references = tokenizer.batch_decode(inputs.cpu().tolist(), skip_special_tokens=True)
        bleu_metrics = compute_accuracy_metrics(predictions, references)

        final_metrics: Dict[str, Any] = {
            "bleu": bleu_metrics,
            "config": cfg.__dict__,
            "log_path": str(log_path),
            "lora_r": args.lora_r,
            "lora_alpha": args.lora_alpha,
        }
        report_final_metrics(final_metrics, cfg.output_dir / "final_metrics.json")
    finally:
        stop_background_monitor(monitor_process)


if __name__ == "__main__":
    main()
