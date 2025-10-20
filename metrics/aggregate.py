"""Aggregate metrics across benchmark runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Root directory with run outputs")
    parser.add_argument("--output", type=Path, default=Path("metrics/summary.csv"))
    return parser.parse_args()


def collect_metrics(root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for metrics_path in root.glob("**/metrics.json"):
        with metrics_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data["run"] = metrics_path.parent.name
        data["path"] = str(metrics_path)
        rows.append(data)
    return rows


def main() -> None:
    args = parse_args()
    rows = collect_metrics(args.root)
    if not rows:
        return
    df = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
