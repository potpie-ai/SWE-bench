#!/usr/bin/env python3
"""
Compile all JSON files from the evals folder into a single JSON array.

This script reads all .json files (excluding summary.jsonl) from the evals
directory and combines them into a single JSON file with all results in an array.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load a JSON file and return its contents."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        raise


def compile_results(
    evals_dir: Path, output_file: Path, exclude_patterns: Optional[List[str]] = None
) -> None:
    """
    Compile all JSON files from evals_dir into a single JSON array.

    Args:
        evals_dir: Directory containing JSON evaluation files
        output_file: Path to write the compiled JSON array
        exclude_patterns: List of filename patterns to exclude (default: ["summary.jsonl"])
    """
    if exclude_patterns is None:
        exclude_patterns = ["summary.jsonl"]

    if not evals_dir.exists():
        raise FileNotFoundError(f"Evals directory not found: {evals_dir}")

    if not evals_dir.is_dir():
        raise ValueError(f"Path is not a directory: {evals_dir}")

    # Find all JSON files, excluding specified patterns
    json_files = []
    for file_path in evals_dir.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() != ".json":
            continue
        if any(pattern in file_path.name for pattern in exclude_patterns):
            logger.debug(f"Skipping excluded file: {file_path.name}")
            continue
        json_files.append(file_path)

    if not json_files:
        logger.warning(f"No JSON files found in {evals_dir}")
        return

    # Sort files for consistent ordering
    json_files.sort(key=lambda p: p.name)

    logger.info(f"Found {len(json_files)} JSON file(s) to compile")

    # Load all JSON files
    all_results = []
    for file_path in json_files:
        try:
            data = load_json_file(file_path)
            # Filter out instances with empty model_patch field
            model_patch = data.get("model_patch", "")
            if not model_patch or not model_patch.strip():
                logger.debug(f"Skipping {file_path.name} - empty model_patch")
                continue
            all_results.append(data)
            logger.debug(f"Loaded {file_path.name}")
        except Exception as e:
            logger.warning(f"Skipping {file_path.name} due to error: {e}")

    if not all_results:
        logger.warning("No valid JSON files were loaded")
        return

    # Write compiled results to output file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully compiled {len(all_results)} result(s) to {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile all JSON files from evals folder into a single JSON array."
    )
    parser.add_argument(
        "--evals-dir",
        type=Path,
        default=Path(__file__).parent / "evals_resolved",
        help="Directory containing evaluation JSON files (default: ./evals)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results" / "compiled_last10_again.json",
        help="Output file path (default: ./results/compiled_remaining.json)",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=["summary.jsonl"],
        help="Filename patterns to exclude (default: summary.jsonl)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        compile_results(
            evals_dir=args.evals_dir,
            output_file=args.output,
            exclude_patterns=args.exclude,
        )
    except Exception as e:
        logger.error(f"Failed to compile results: {e}")
        raise


if __name__ == "__main__":
    main()
