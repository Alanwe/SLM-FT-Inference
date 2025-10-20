"""DeepSpeed fine-tuning demo."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import torch
from transformers import (
    AutoModelForCausalLM,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

from training.utils.config import DEFAULT_CONFIG, TrainingConfig
from training.utils.dataset import prepare_dataset
from training.utils.logging_utils import configure_logging, load_env
from training.utils.metrics import (
    compute_accuracy_metrics,
    report_final_metrics,
    start_background_monitor,
    stop_background_monitor,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune with DeepSpeed")
    parser.add_argument("--config", type=Path, default=None, help="Path to YAML config")
    parser.add_argument("--deepspeed", type=Path, default=Path("training/deepspeed/ds_config_zero3.json"), help="DeepSpeed config file")
    parser.add_argument("--env-file", type=str, default=None)
    return parser.parse_args()


def load_config(path: Path | None) -> TrainingConfig:
    if path is None:
        return DEFAULT_CONFIG
    cfg = TrainingConfig.from_yaml(path)
    return cfg


def main() -> None:
    args = parse_args()
    load_env(args.env_file)

    cfg = load_config(args.config)
    cfg.deepspeed_config = args.deepspeed

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = configure_logging(cfg.output_dir)
    monitor_process = start_background_monitor(cfg.output_dir / "system_metrics.jsonl", interval=5.0)

    try:
        tokenized = prepare_dataset(cfg.dataset_path, cfg.base_model_name, cfg.max_seq_length)
        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenized.tokenizer, mlm=False)

        model = AutoModelForCausalLM.from_pretrained(cfg.base_model_name, torch_dtype=torch.bfloat16)
        model.resize_token_embeddings(len(tokenized.tokenizer))

        training_args = TrainingArguments(
            output_dir=str(cfg.output_dir),
            num_train_epochs=cfg.num_epochs,
            per_device_train_batch_size=cfg.batch_size,
            gradient_accumulation_steps=cfg.gradient_accumulation_steps,
            learning_rate=cfg.learning_rate,
            lr_scheduler_type=cfg.lr_scheduler_type,
            logging_steps=cfg.logging_steps,
            evaluation_strategy="steps",
            eval_steps=cfg.evaluation_steps,
            save_strategy="epoch",
            deepspeed=str(args.deepspeed),
            gradient_checkpointing=cfg.gradient_checkpointing,
            bf16=True,
            report_to=["none"],
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized.dataset,
            eval_dataset=tokenized.dataset.select(range(min(200, len(tokenized.dataset)))),
            data_collator=data_collator,
            tokenizer=tokenized.tokenizer,
        )

        trainer.train()
        trainer.save_model(cfg.output_dir)

        eval_samples = tokenized.dataset.select(range(min(16, len(tokenized.dataset))))
        inputs = torch.tensor(eval_samples["input_ids"], device=trainer.model.device)
        generations = trainer.model.generate(max_length=cfg.max_seq_length, input_ids=inputs)
        predictions = tokenized.tokenizer.batch_decode(generations, skip_special_tokens=True)
        references = tokenized.tokenizer.batch_decode(inputs.cpu().tolist(), skip_special_tokens=True)
        bleu_metrics = compute_accuracy_metrics(predictions, references)

        final_metrics: Dict[str, Any] = {
            "bleu": bleu_metrics,
            "config": cfg.__dict__,
            "log_path": str(log_path),
            "deepspeed_config": str(args.deepspeed),
        }
        report_final_metrics(final_metrics, cfg.output_dir / "final_metrics.json")
    finally:
        stop_background_monitor(monitor_process)


if __name__ == "__main__":
    main()
