"""Download fine-tuning dataset locally for offline runs."""
from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=str, default="philschmid/guanaco-belle-7b")
    parser.add_argument("--split", type=str, default="train")
    parser.add_argument("--output", type=Path, default=Path("data/cache"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_dataset(args.dataset, split=args.split)
    args.output.mkdir(parents=True, exist_ok=True)
    dataset.save_to_disk(str(args.output / args.split))


if __name__ == "__main__":
    main()
