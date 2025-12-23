#!/usr/bin/env python3
"""
Script to dump the full SWE-bench_Lite dataset from Hugging Face into a dataset.json file.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Iterable, cast

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_swebench_lite_instances(split: str = "test") -> List[Dict[str, Any]]:
    """
    Load SWE-bench Lite instances from Hugging Face.

    Args:
        split: Dataset split to load ("test" or "dev")

    Returns:
        List of all instances from the dataset
    """
    try:
        from datasets import load_dataset  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "Missing optional dependency 'datasets'. Install it with "
            "`pip install datasets` to load SWE-bench Lite instances."
        ) from exc

    logger.info("Loading SWE-bench Lite (%s split) from Hugging Face", split)
    dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split=split)
    records = cast(Iterable[Dict[Any, Any]], dataset)
    return [{str(key): value for key, value in record.items()} for record in records]


def main():
    """Main function to dump the dataset."""
    project_root = Path(__file__).resolve().parent
    output_file = project_root / "dataset.json"

    logger.info("Loading instances from SWE-bench_Lite (test split)")
    instances = load_swebench_lite_instances(split="test")

    logger.info(f"Loaded {len(instances)} instances")

    # Write to output file
    logger.info(f"Writing dataset to {output_file}")
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(instances, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully wrote {len(instances)} instances to {output_file}")
    logger.info(f"Output file size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
