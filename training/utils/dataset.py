"""Dataset utilities for fine-tuning demos."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from datasets import Dataset
from transformers import AutoTokenizer


@dataclass
class TokenizedDataset:
    dataset: Dataset
    tokenizer: AutoTokenizer


def load_text_dataset(path: Path) -> Dataset:
    with path.open("r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    return Dataset.from_list(records)


def tokenize_dataset(dataset: Dataset, tokenizer: AutoTokenizer, max_length: int) -> Dataset:
    def tokenize_fn(batch: dict[str, list[str]]):
        texts: Iterable[str] = batch.get("text") or batch.get("content") or batch.get("instruction")
        if texts is None:
            raise KeyError("Dataset must contain a `text`, `content`, or `instruction` field")
        tokens = tokenizer(
            list(texts),
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    keep_cols = set(["input_ids", "attention_mask", "labels"])
    remove_cols = [col for col in dataset.column_names if col not in keep_cols]
    return dataset.map(tokenize_fn, batched=True, remove_columns=remove_cols)


def prepare_dataset(path: Path, tokenizer_name: str, max_seq_length: int) -> TokenizedDataset:
    dataset = load_text_dataset(path)
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenized = tokenize_dataset(dataset, tokenizer, max_seq_length)
    return TokenizedDataset(dataset=tokenized, tokenizer=tokenizer)
