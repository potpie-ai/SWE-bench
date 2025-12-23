#!/usr/bin/env python3
"""
Script to extract all patches from dataset.json and write them to a text file.
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def extract_patches(dataset_path: Path, output_path: Path) -> None:
    """
    Extract patches from dataset.json and write to output file.
    
    Args:
        dataset_path: Path to the dataset.json file
        output_path: Path to the output text file
    """
    logger.info(f"Loading dataset from {dataset_path}")
    
    with dataset_path.open("r", encoding="utf-8") as f:
        instances = json.load(f)
    
    logger.info(f"Loaded {len(instances)} instances")
    
    logger.info(f"Writing patches to {output_path}")
    
    with output_path.open("w", encoding="utf-8") as f:
        for idx, instance in enumerate(instances, 1):
            instance_id = instance.get("instance_id", f"instance_{idx}")
            patch = instance.get("patch", "")
            
            # Write separator and instance info
            f.write("=" * 80 + "\n")
            f.write(f"Instance {idx}: {instance_id}\n")
            f.write("=" * 80 + "\n\n")
            
            if patch:
                f.write(patch)
                # Add trailing newline if patch doesn't end with one
                if not patch.endswith("\n"):
                    f.write("\n")
            else:
                f.write("[No patch available]\n")
            
            # Add spacing between instances
            f.write("\n\n")
    
    logger.info(f"Successfully extracted {len(instances)} patches to {output_path}")
    logger.info(f"Output file size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    """Main function to extract patches."""
    project_root = Path(__file__).resolve().parent
    dataset_path = project_root / "dataset.json"
    output_path = project_root / "patches.txt"
    
    if not dataset_path.exists():
        logger.error(f"Dataset file not found: {dataset_path}")
        return
    
    extract_patches(dataset_path, output_path)


if __name__ == "__main__":
    main()

