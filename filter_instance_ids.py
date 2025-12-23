#!/usr/bin/env python3
"""
Script to filter out instance_ids that exist in compiled.json
"""

import json

# Read compiled.json and extract all instance_ids
compiled_file = "results/compiled_resolved.json"
with open(compiled_file, "r") as f:
    compiled_data = json.load(f)

# Extract instance_ids from compiled.json
compiled_instance_ids = {
    item["instance_id"] for item in compiled_data if "instance_id" in item
}
print(f"Found {len(compiled_instance_ids)} instance_ids in compiled.json")

# Placeholder list - fill this with your instance_ids
instance_ids = [
    "django__django-11099",
    "django__django-10914",
    "django__django-11815",
    "django__django-12983",
    "django__django-12700",
    "django__django-12284",
    "django__django-13028",
    "django__django-12915",
    "django__django-13230",
    "django__django-13710",
    "django__django-13757",
    "django__django-13964",
    "django__django-14382",
    "django__django-14608",
    "django__django-14752",
    "django__django-14915",
    "django__django-14411",
    "django__django-14855",
    "django__django-15789",
    "django__django-15213",
    "django__django-15851",
    "django__django-16041",
    "django__django-16379",
    "django__django-16595",
    "django__django-16527",
    "django__django-16139",
    "django__django-16255",
    "django__django-16873",
    "mwaskom__seaborn-3010",
    "pydata__xarray-5131",
    "astropy__astropy-14995",
    "scikit-learn__scikit-learn-10297",
    "scikit-learn__scikit-learn-13439",
    "scikit-learn__scikit-learn-13779",
    "scikit-learn__scikit-learn-13241",
    "scikit-learn__scikit-learn-14894",
    "scikit-learn__scikit-learn-25570",
    "sphinx-doc__sphinx-7975",
    "sphinx-doc__sphinx-8435",
    "sphinx-doc__sphinx-10325",
    "sphinx-doc__sphinx-8713",
    "matplotlib__matplotlib-23913",
    "matplotlib__matplotlib-24149",
    "matplotlib__matplotlib-23964",
    "matplotlib__matplotlib-24970",
    "psf__requests-3362",
    "pytest-dev__pytest-7373",
    "pytest-dev__pytest-5227",
    "pytest-dev__pytest-11143",
    "sympy__sympy-12481",
    "sympy__sympy-13480",
    "sympy__sympy-15345",
    "sympy__sympy-14774",
    "psf__requests-863",
    "sympy__sympy-18621",
    "sympy__sympy-16988",
    "sympy__sympy-17022",
    "sympy__sympy-22714",
    "sympy__sympy-24152",
    "sympy__sympy-24213",
    "sympy__sympy-20154",
]

print(f"Found {len(instance_ids)} instance_ids in input list")

# Filter out instance_ids that exist in compiled.json
filtered_instance_ids = [
    instance_id
    for instance_id in instance_ids
    if instance_id not in compiled_instance_ids
]

print(
    f"Filtered to {len(filtered_instance_ids)} instance_ids (removed {len(instance_ids) - len(filtered_instance_ids)})"
)

# Output to a new JSON file
output_file = "filtered_instance_ids.json"
with open(output_file, "w") as f:
    json.dump(filtered_instance_ids, f, indent=2)

print(f"Output written to {output_file}")
