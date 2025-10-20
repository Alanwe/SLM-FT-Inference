"""Utility to fetch demo datasets for fine-tuning."""
from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Download dataset for fine-tuning demos")
    parser.add_argument("--dataset", required=True, help="Dataset name on the Hugging Face Hub")
    parser.add_argument("--subset", default=None, help="Optional dataset configuration or subset")
    parser.add_argument("--split", default="train", help="Dataset split to download")
    parser.add_argument("--sample-size", type=int, default=2000, help="Number of rows to sample for the demo")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    ds = load_dataset(args.dataset, args.subset, split=args.split)
    if args.sample_size and len(ds) > args.sample_size:
        ds = ds.select(range(args.sample_size))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"{args.dataset.replace('/', '_')}_{args.split}.jsonl"
    ds.to_json(str(output_path))
    print(f"Saved dataset to {output_path}")


if __name__ == "__main__":
    main()
