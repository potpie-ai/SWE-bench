#!/usr/bin/env python3
"""
Merge compiled.json and compiled_resolved.json.

If an instance exists in both files, the instance from compiled_resolved.json
takes precedence in the merged output.
"""

import json
import sys
from pathlib import Path


def merge_compiled_files(compiled_path, resolved_path, output_path):
    """
    Merge two compiled JSON files.

    Args:
        compiled_path: Path to compiled.json
        resolved_path: Path to compiled_resolved.json
        output_path: Path where merged output will be written
    """
    # Load both JSON files
    print(f"Loading {compiled_path}...")
    with open(compiled_path, "r") as f:
        compiled_data = json.load(f)

    print(f"Loading {resolved_path}...")
    with open(resolved_path, "r") as f:
        resolved_data = json.load(f)

    print(f"  compiled.json: {len(compiled_data)} instances")
    print(f"  compiled_resolved.json: {len(resolved_data)} instances")

    # Create a dictionary keyed by instance_id to deduplicate
    merged_dict = {}

    # Track duplicates within each file
    compiled_ids_seen = set()
    compiled_duplicates = 0
    resolved_ids_seen = set()
    resolved_duplicates = 0

    # First, add all instances from compiled.json (deduplicates within this file)
    for instance in compiled_data:
        instance_id = instance.get("instance_id")
        if instance_id:
            if instance_id in compiled_ids_seen:
                compiled_duplicates += 1
            compiled_ids_seen.add(instance_id)
            merged_dict[instance_id] = instance

    # Then, overwrite/add instances from compiled_resolved.json
    # This ensures compiled_resolved.json takes precedence
    overwritten_count = 0
    for instance in resolved_data:
        instance_id = instance.get("instance_id")
        if instance_id:
            if instance_id in resolved_ids_seen:
                resolved_duplicates += 1
            resolved_ids_seen.add(instance_id)

            if instance_id in merged_dict:
                overwritten_count += 1
            merged_dict[instance_id] = instance

    # Convert back to list (already deduplicated)
    merged_list = list(merged_dict.values())

    print(f"\nDeduplication summary:")
    if compiled_duplicates > 0:
        print(f"  Duplicates in compiled.json: {compiled_duplicates}")
    if resolved_duplicates > 0:
        print(f"  Duplicates in compiled_resolved.json: {resolved_duplicates}")
    print(f"\nMerged result: {len(merged_list)} unique instances")
    if overwritten_count > 0:
        print(f"  Instances overwritten by compiled_resolved.json: {overwritten_count}")

    # Write output
    print(f"\nWriting merged output to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(merged_list, f, indent=2)

    print("Merge complete!")


def main():
    """Main entry point."""
    # Default paths
    script_dir = Path(__file__).parent
    results_dir = script_dir / "results"

    compiled_path = results_dir / "compiled_final_again.json"
    resolved_path = results_dir / "compiled_last10_again.json"
    output_path = results_dir / "compiled_final_again.json"

    # Allow custom paths via command line arguments
    if len(sys.argv) >= 2:
        compiled_path = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        resolved_path = Path(sys.argv[2])
    if len(sys.argv) >= 4:
        output_path = Path(sys.argv[3])

    # Validate input files exist
    if not compiled_path.exists():
        print(f"Error: {compiled_path} does not exist", file=sys.stderr)
        sys.exit(1)

    if not resolved_path.exists():
        print(f"Error: {resolved_path} does not exist", file=sys.stderr)
        sys.exit(1)

    merge_compiled_files(compiled_path, resolved_path, output_path)


if __name__ == "__main__":
    main()
